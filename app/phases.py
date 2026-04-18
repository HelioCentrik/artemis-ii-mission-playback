# app/phases.py
#
# Detect the six mission phase timestamps from the in-memory DB at startup.
# Uses trigger conditions from Roadmap.md. Results are cached in _PHASE_DATA
# after the first call to get_phases().

import duckdb

from app.config import PHASES



# Clearance from r_moon minimum before we declare "return coast has begun"
_RETURN_COAST_MARGIN_KM = 5_000.0

_PHASE_DATA: list[dict] | None = None


def _detect(con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Run all six phase detection queries and return annotated phase list."""

    # ── 1. Early Coast — first row ───────────────────────────────────────
    mission_start = con.execute(
        "SELECT MIN(datetime_utc) FROM orion_trajectory"
    ).fetchone()[0]

    # ── 2. TLI Burn — peak speed ─────────────────────────────────────────
    # TLI fires very early (dataset starts at T+3.5h); constraining to 12h
    # prevents the faster end-of-mission return approach from winning the
    # global max.
    tli_time = con.execute(
        """
        SELECT datetime_utc
        FROM   v_kinematics
        WHERE  datetime_utc <= ? + INTERVAL 12 HOURS
        ORDER  BY speed_kms DESC
        LIMIT  1
        """,
        [mission_start],
    ).fetchone()[0]

    # ── 3. Trans-Lunar Coast — first row where C3 crosses zero ───────────
    tlc_time = con.execute(
        """
        SELECT datetime_utc
        FROM   v_kinematics
        WHERE  c3_km2s2 > 0
        ORDER  BY datetime_utc ASC
        LIMIT  1
        """
    ).fetchone()[0]

    # ── 5. Closest Approach — global r_moon minimum ──────────────────────
    # (Detected before phase 4 — LA detection depends on this timestamp.)
    ca_row = con.execute(
        "SELECT datetime_utc, r_moon_km FROM v_earth_moon ORDER BY r_moon_km ASC LIMIT 1"
    ).fetchone()
    ca_time, ca_r_moon = ca_row

    # ── 4. Lunar Approach — first row inside 100,000 km of the Moon ──────
    # r_moon decreases monotonically from ~406k km to closest approach, so
    # a local-max approach just finds the start of the outbound leg. A
    # threshold at 100k km (inside lunar sphere of influence) is a much
    # cleaner "final approach" marker.
    la_result = con.execute(
        """
        SELECT datetime_utc
        FROM   v_earth_moon
        WHERE  r_moon_km   < 100000.0
          AND  datetime_utc < ?
        ORDER  BY datetime_utc ASC
        LIMIT  1
        """,
        [ca_time],
    ).fetchone()

    la_time = la_result[0] if la_result else tlc_time

    # Fallback: if no clean local max detected, use TLC timestamp
    la_time = la_result[0] if la_result else tlc_time

    # ── 6. Return Coast — first row after flyby with meaningful separation ─
    rc_result = con.execute(
        """
        SELECT datetime_utc
        FROM   v_earth_moon
        WHERE  datetime_utc > ?
          AND  r_moon_km    > ? + ?
        ORDER  BY datetime_utc ASC
        LIMIT  1
        """,
        [ca_time, ca_r_moon, _RETURN_COAST_MARGIN_KM],
    ).fetchone()

    # Fallback: if margin query fails, take first row after closest approach
    if rc_result is None:
        rc_result = con.execute(
            "SELECT datetime_utc FROM v_earth_moon WHERE datetime_utc > ? "
            "ORDER BY datetime_utc ASC LIMIT 1",
            [ca_time],
        ).fetchone()

    rc_time = rc_result[0]

    # ── Assemble results ─────────────────────────────────────────────────
    phase_timestamps = [
        mission_start,   # Early Coast
        tlc_time,        # Trans-Lunar Coast
        la_time,         # Lunar Approach
        ca_time,         # Closest Approach
        rc_time,         # Return Coast
    ]

    return [
        {
            **phase,
            "datetime_utc": dt,
            "met_seconds":  int((dt - mission_start).total_seconds()),
        }
        for phase, dt in zip(PHASES, phase_timestamps)
    ]


def get_phases() -> list[dict]:
    """
    Return the annotated phase list, detecting from DB on first call.

    Each entry is the corresponding PHASES dict from config.py extended with:
        datetime_utc : datetime   — UTC timestamp of phase start
        met_seconds  : int        — mission elapsed time in seconds
    """
    global _PHASE_DATA
    if _PHASE_DATA is None:
        from app.db import get_con
        _PHASE_DATA = _detect(get_con())
    return _PHASE_DATA


def get_phase_datetimes() -> list:
    """Convenience accessor: ordered list of phase datetime_utc values."""
    return [p["datetime_utc"] for p in get_phases()]