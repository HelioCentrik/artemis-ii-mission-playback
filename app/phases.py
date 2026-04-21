# app/phases.py
#
# Detect all mission event timestamps from the in-memory DB at startup.
#
# Resolution priority per phase key:
#   1. PHASE_HARDCODED_TIMES (config.py) — confirmed ops events; snapped to
#      nearest DB row via _snap_to_db().
#   2. Detector function in _DETECTORS — physics/derived events that have no
#      known wall-clock time (c3_zero) or structural anchors (parking_orbit,
#      dataset_close, etc.).
#
# Detection runs in _DETECTION_ORDER. Dependencies must precede dependents:
#   tli_burn       → outbound_coast
#   closest_approach → transearth_coast, earth_approach

import duckdb
from datetime import datetime, timedelta
from typing import Callable

from app.config import PHASE_REGISTRY, PHASE_HARDCODED_TIMES, LAUNCH_TIME


# ── MET helper ────────────────────────────────────────────────────────────────

_LAUNCH_DT: datetime = datetime.fromisoformat(LAUNCH_TIME)


def _met(dt: datetime) -> int:
    """Mission elapsed time in whole seconds from launch (T=0)."""
    return int((dt - _LAUNCH_DT).total_seconds())


# ── Hardcoded timestamp resolver ──────────────────────────────────────────────

def _snap_to_db(con: duckdb.DuckDBPyConnection, iso_str: str) -> datetime:
    """
    Snap an ISO-8601 UTC string to the nearest row in orion_trajectory.

    The 1-minute ephemeris spine starts at 01:59 UTC, so hardcoded times
    like 23:49:00 won't land exactly on a row. This finds the closest match
    by epoch difference, which is always ≤ 30 seconds off.
    """
    return con.execute("""
        SELECT datetime_utc
        FROM   orion_trajectory
        ORDER  BY ABS(EPOCH(datetime_utc) - EPOCH(CAST(? AS TIMESTAMP)))
        LIMIT  1
    """, [iso_str]).fetchone()[0]


# ── Phase detectors ───────────────────────────────────────────────────────────
# Only phases NOT in PHASE_HARDCODED_TIMES need a detector.
# Signature: (con, **resolved_so_far) → datetime | None

def _detect_parking_orbit(con, **_) -> datetime:
    """First row — Orion already in LEO, ~T+3h24m from launch."""
    return con.execute(
        "SELECT MIN(datetime_utc) FROM orion_trajectory"
    ).fetchone()[0]


def _detect_c3_zero(con, **_) -> datetime:
    """
    First row where C3 >= 0 — Orion crosses Earth escape energy.
    This is the physics consequence of TLI, not the burn itself.
    Typically occurs a few minutes after TLI ignition as the burn
    accelerates the spacecraft past escape velocity.
    """
    return con.execute("""
        SELECT datetime_utc
        FROM   v_kinematics
        WHERE  c3_km2s2 >= 0.0
        ORDER  BY datetime_utc ASC
        LIMIT  1
    """).fetchone()[0]


def _detect_outbound_coast(con, *, tli_burn: datetime, **_) -> datetime:
    """
    First row after TLI where r_earth crosses 200,000 km outbound.
    Roughly half the Earth–Moon distance — solidly mid-coast.
    """
    return con.execute("""
        SELECT datetime_utc
        FROM   v_kinematics
        WHERE  datetime_utc > ?
          AND  rg_km        >= 200000.0
        ORDER  BY datetime_utc ASC
        LIMIT  1
    """, [tli_burn]).fetchone()[0]


def _detect_transearth_coast(con, *, closest_approach: datetime, **_) -> datetime:
    """
    Temporal midpoint of the return leg (closest approach → dataset close).
    No single physics event marks 'halfway home'; midpoint fills the return
    arc with a meaningful scrubber jump point.
    """
    dataset_close = con.execute(
        "SELECT MAX(datetime_utc) FROM orion_trajectory"
    ).fetchone()[0]
    mid_dt = closest_approach + timedelta(
        seconds=int((dataset_close - closest_approach).total_seconds() / 2)
    )
    return con.execute("""
        SELECT datetime_utc
        FROM   orion_trajectory
        WHERE  datetime_utc >= ?
        ORDER  BY datetime_utc ASC
        LIMIT  1
    """, [mid_dt]).fetchone()[0]


def _detect_earth_approach(con, *, closest_approach: datetime, **_) -> datetime:
    """First row after closest approach where r_earth drops below 100,000 km."""
    return con.execute("""
        SELECT datetime_utc
        FROM   v_kinematics
        WHERE  datetime_utc > ?
          AND  rg_km        < 100000.0
        ORDER  BY datetime_utc ASC
        LIMIT  1
    """, [closest_approach]).fetchone()[0]


def _detect_dataset_close(con, **_) -> datetime:
    """Last row — 'Last Known Position' before reentry plasma blackout."""
    return con.execute(
        "SELECT MAX(datetime_utc) FROM orion_trajectory"
    ).fetchone()[0]


# ── Registries ────────────────────────────────────────────────────────────────

_DETECTORS: dict[str, Callable] = {
    "parking_orbit":    _detect_parking_orbit,
    "c3_zero":          _detect_c3_zero,
    "outbound_coast":   _detect_outbound_coast,
    "transearth_coast": _detect_transearth_coast,
    "earth_approach":   _detect_earth_approach,
    "dataset_close":    _detect_dataset_close,
}

# Hardcoded keys still appear here so their resolved timestamps are available
# as **kwargs for any detector that depends on them (e.g. outbound_coast
# needs tli_burn, transearth_coast needs closest_approach).
_DETECTION_ORDER: tuple[str, ...] = (
    "parking_orbit",
    "perigee_raise",        # hardcoded
    "tli_burn",             # hardcoded → outbound_coast depends on it
    "c3_zero",
    "outbound_coast",
    "otc2_outbound",        # hardcoded
    "lunar_soi_entry",      # hardcoded
    "closest_approach",     # hardcoded → transearth_coast, earth_approach depend on it
    "lunar_soi_exit",       # hardcoded
    "transearth_coast",
    "return_burn_1",        # hardcoded
    "return_burn_2",        # hardcoded
    "earth_approach",
    "dataset_close",
)


# ── Cache + builder ───────────────────────────────────────────────────────────

_PHASE_DATA: list[dict] | None = None


def _build_phases(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """
    Resolve all phase timestamps in dependency order.

    For each key in _DETECTION_ORDER:
      - If key is in PHASE_HARDCODED_TIMES → snap ISO string to nearest DB row
      - Else → call the detector, passing resolved timestamps as **kwargs

    Returns the full phase list in PHASE_REGISTRY order, each entry extended
    with datetime_utc, met_seconds, and scrubber_pct (where scrubber=True).
    """
    resolved: dict[str, datetime | None] = {}

    for key in _DETECTION_ORDER:
        try:
            if key in PHASE_HARDCODED_TIMES:
                resolved[key] = _snap_to_db(con, PHASE_HARDCODED_TIMES[key])
            else:
                resolved[key] = _DETECTORS[key](con, **resolved)
        except Exception as exc:
            print(f"  [phases] WARNING: {key} resolution failed — {exc}")
            resolved[key] = None

    # Scrubber % scaling: span from dataset start to close
    dataset_start_dt = resolved.get("parking_orbit")
    dataset_close_dt = resolved.get("dataset_close")
    dataset_span_s   = int((dataset_close_dt - dataset_start_dt).total_seconds())

    result = []
    for phase in PHASE_REGISTRY:
        key = phase["key"]
        dt  = resolved.get(key)
        if dt is None:
            continue

        met_s = _met(dt)
        entry = {**phase, "datetime_utc": dt, "met_seconds": met_s}

        if phase["scrubber"]:
            entry["scrubber_pct"] = (
                (dt - dataset_start_dt).total_seconds() / dataset_span_s * 100.0
            )
        result.append(entry)

    return result


def get_phases() -> list[dict]:
    """
    Return the full annotated phase list, detecting on first call then caching.
    """
    global _PHASE_DATA
    if _PHASE_DATA is None:
        from app.db import get_con
        _PHASE_DATA = _build_phases(get_con())
    return _PHASE_DATA


def get_scrubber_phases() -> list[dict]:
    """Phases with scrubber=True, in registry order. Includes scrubber_pct."""
    return [p for p in get_phases() if p["scrubber"]]


def get_arc_marker_phases() -> list[dict]:
    """Phases with arc_marker=True, in registry order."""
    return [p for p in get_phases() if p["arc_marker"]]