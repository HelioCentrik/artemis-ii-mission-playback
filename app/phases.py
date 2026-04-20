# app/phases.py
#
# Detect all mission event timestamps from the in-memory DB at startup.
# One detector function per phase key. Results are cached after the first
# call to get_phases().
#
# Detection order is explicit — dependencies must precede dependents.
# Downstream consumers filter by phase["scrubber"] or phase["arc_marker"];
# this module doesn't care about rendering.

import duckdb
from datetime import datetime, timedelta
from typing import Callable

from app.config import PHASE_REGISTRY, LAUNCH_TIME



# ── MET helper ────────────────────────────────────────────────────────────────

_LAUNCH_DT: datetime = datetime.fromisoformat(LAUNCH_TIME)


def _met(dt: datetime) -> int:
    """Mission elapsed time in whole seconds from launch (T=0)."""
    return int((dt - _LAUNCH_DT).total_seconds())


# ── Phase detectors ───────────────────────────────────────────────────────────
# Each function signature: (con, **resolved_so_far) → datetime | None
# Named kwargs match PHASE_REGISTRY keys so passing **resolved works cleanly.

def _detect_parking_orbit(con, **_) -> datetime:
    """First row in dataset — Orion already in LEO, ~T+3h24m from launch."""
    return con.execute(
        "SELECT MIN(datetime_utc) FROM orion_trajectory"
    ).fetchone()[0]


def _detect_tli_burn(con, **_) -> datetime:
    """
    Speed peak within first 36 hours of dataset.
    TLI fires at perigee of the parking orbit — the highest-speed moment
    in the early mission window.
    """
    mission_start = con.execute(
        "SELECT MIN(datetime_utc) FROM orion_trajectory"
    ).fetchone()[0]
    return con.execute("""
        SELECT datetime_utc
        FROM   v_kinematics
        WHERE  datetime_utc <= ? + INTERVAL 36 HOURS
        ORDER  BY speed_kms DESC
        LIMIT  1
    """, [mission_start]).fetchone()[0]


def _detect_apogee(con, **_) -> datetime:
    """
    Speed minimum in first 14 hours = parking orbit apogee.
    Orion coasts to the high point of its elliptical parking orbit before
    falling back toward perigee for the TLI burn.
    """
    mission_start = con.execute(
        "SELECT MIN(datetime_utc) FROM orion_trajectory"
    ).fetchone()[0]
    return con.execute("""
        SELECT datetime_utc
        FROM   v_kinematics
        WHERE  datetime_utc <= ? + INTERVAL 14 HOURS
        ORDER  BY speed_kms ASC
        LIMIT  1
    """, [mission_start]).fetchone()[0]


def _detect_closest_approach(con, **_) -> datetime:
    """Global r_moon minimum — the primary mission event."""
    return con.execute(
        "SELECT datetime_utc FROM v_earth_moon ORDER BY r_moon_km ASC LIMIT 1"
    ).fetchone()[0]


def _detect_outbound_coast(con, *, tli_burn: datetime, **_) -> datetime:
    """
    First row after TLI where r_earth crosses 200,000 km outbound.
    Roughly half the Earth–Moon distance — Orion is clearly mid-coast.
    """
    return con.execute("""
        SELECT datetime_utc
        FROM   v_kinematics
        WHERE  datetime_utc > ?
          AND  rg_km        >= 200000.0
        ORDER  BY datetime_utc ASC
        LIMIT  1
    """, [tli_burn]).fetchone()[0]


def _detect_mid_course(
    con, *, outbound_coast: datetime, closest_approach: datetime, **_
) -> datetime | None:
    """
    Mid-course correction burn: largest local speed spike between outbound
    coast and closest approach, detected as the row where speed exceeds both
    its immediate neighbors by the widest margin.
    Returns None if no qualifying spike is found.
    """
    result = con.execute("""
        SELECT k1.datetime_utc
        FROM   v_kinematics k1
        JOIN   v_kinematics k2
               ON k2.datetime_utc = k1.datetime_utc - INTERVAL 1 MINUTE
        JOIN   v_kinematics k3
               ON k3.datetime_utc = k1.datetime_utc + INTERVAL 1 MINUTE
        WHERE  k1.datetime_utc >  ?
          AND  k1.datetime_utc <  ?
          AND  k1.speed_kms    >  k2.speed_kms
          AND  k1.speed_kms    >  k3.speed_kms
          AND (k1.speed_kms    -  k2.speed_kms) > 0.05
        ORDER  BY (k1.speed_kms - k2.speed_kms + k1.speed_kms - k3.speed_kms) DESC
        LIMIT  1
    """, [outbound_coast, closest_approach]).fetchone()
    return result[0] if result else None


def _detect_grav_crossover(con, *, closest_approach: datetime, **_) -> datetime:
    """
    First row where Moon's gravitational pull exceeds Earth's:
        GM_MOON / r_moon² >= GM_EARTH / r_earth²
    """
    return con.execute("""
        SELECT e.datetime_utc
        FROM   v_earth_moon e
        JOIN   v_kinematics k ON e.datetime_utc = k.datetime_utc
        WHERE  (4902.8001   / (e.r_moon_km * e.r_moon_km))
            >= (398600.4418 / (k.rg_km     * k.rg_km    ))
          AND  e.datetime_utc < ?
        ORDER  BY e.datetime_utc ASC
        LIMIT  1
    """, [closest_approach]).fetchone()[0]


def _detect_lunar_soi_entry(con, *, closest_approach: datetime, **_) -> datetime:
    """First row inside 66,000 km of the Moon before closest approach."""
    return con.execute("""
        SELECT datetime_utc
        FROM   v_earth_moon
        WHERE  r_moon_km    < 66000.0
          AND  datetime_utc < ?
        ORDER  BY datetime_utc ASC
        LIMIT  1
    """, [closest_approach]).fetchone()[0]


def _detect_lunar_soi_exit(con, *, closest_approach: datetime, **_) -> datetime:
    """First row outside 66,000 km of the Moon after closest approach."""
    return con.execute("""
        SELECT datetime_utc
        FROM   v_earth_moon
        WHERE  r_moon_km    > 66000.0
          AND  datetime_utc > ?
        ORDER  BY datetime_utc ASC
        LIMIT  1
    """, [closest_approach]).fetchone()[0]


def _detect_transearth_coast(con, *, closest_approach: datetime, **_) -> datetime:
    """
    Temporal midpoint of the return leg (closest approach → dataset close).
    No single physics event marks 'halfway home' — the midpoint fills the
    return arc with a meaningful scrubber jump point.
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


def _detect_distance_record(con, **_) -> datetime:
    """Maximum r_earth across the full mission (farthest humans from Earth)."""
    return con.execute(
        "SELECT datetime_utc FROM v_kinematics ORDER BY rg_km DESC LIMIT 1"
    ).fetchone()[0]


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
    "tli_burn":         _detect_tli_burn,
    "apogee":           _detect_apogee,
    "outbound_coast":   _detect_outbound_coast,
    "mid_course":       _detect_mid_course,
    "grav_crossover":   _detect_grav_crossover,
    "lunar_soi_entry":  _detect_lunar_soi_entry,
    "closest_approach": _detect_closest_approach,
    "lunar_soi_exit":   _detect_lunar_soi_exit,
    "transearth_coast": _detect_transearth_coast,
    "distance_record":  _detect_distance_record,
    "earth_approach":   _detect_earth_approach,
    "dataset_close":    _detect_dataset_close,
}

# Dependencies must precede their dependents.
_DETECTION_ORDER: tuple[str, ...] = (
    "parking_orbit",
    "tli_burn",
    "apogee",
    "closest_approach",    # anchor — required by: outbound_coast, mid_course,
                           #   grav_crossover, lunar_soi_entry/exit,
                           #   transearth_coast, earth_approach
    "outbound_coast",
    "mid_course",
    "grav_crossover",
    "lunar_soi_entry",
    "lunar_soi_exit",
    "transearth_coast",
    "distance_record",
    "earth_approach",
    "dataset_close",
)


# ── Cache + builder ───────────────────────────────────────────────────────────

_PHASE_DATA: list[dict] | None = None


def _build_phases(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """
    Run all detectors in dependency order, passing the growing resolved dict
    as **kwargs so each detector can access any previously-computed timestamp.

    Returns the full phase list in PHASE_REGISTRY order. Each entry is
    extended with:
        datetime_utc  : datetime  — UTC timestamp of the event
        met_seconds   : int       — seconds elapsed since launch (T=0)
        scrubber_pct  : float     — 0–100, only present when scrubber=True
    """
    # 1. Detect all timestamps in dependency order
    resolved: dict[str, datetime | None] = {}
    for key in _DETECTION_ORDER:
        try:
            resolved[key] = _DETECTORS[key](con, **resolved)
        except Exception as exc:
            print(f"  [phases] WARNING: {key} detection failed — {exc}")
            resolved[key] = None

    # 2. Total MET span (launch → dataset close) for scrubber_pct scaling
    close_dt    = resolved.get("dataset_close")
    total_met_s = _met(close_dt) if close_dt else 1

    # 3. Build output list in PHASE_REGISTRY order
    result = []
    for phase in PHASE_REGISTRY:
        key = phase["key"]
        dt  = resolved.get(key)
        if dt is None:
            continue

        met_s = _met(dt)
        entry = {**phase, "datetime_utc": dt, "met_seconds": met_s}
        dataset_start_dt = resolved.get("parking_orbit")
        dataset_close_dt = resolved.get("dataset_close")
        dataset_span_s = int((dataset_close_dt - dataset_start_dt).total_seconds())
        if phase["scrubber"]:
            entry["scrubber_pct"] = (
                    (dt - dataset_start_dt).total_seconds() / dataset_span_s * 100.0
            )
        result.append(entry)

    return result


def get_phases() -> list[dict]:
    """
    Return the full annotated phase list, detecting on first call then caching.

    Filter for downstream consumers:
        scrubber dots   → get_scrubber_phases()
        arc markers     → get_arc_marker_phases()
        telemetry nav   → get_scrubber_phases()
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