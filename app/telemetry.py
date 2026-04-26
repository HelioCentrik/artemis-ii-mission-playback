# app/telemetry.py
#
# Telemetry data access layer.
#
# get_telemetry_preload() — full-mission series for all 12 metrics;
#                           cached at module level on first call.
# get_telemetry_at()      — single-row point query; used on phase-click
#                           rebuilds only, not cached.

from __future__ import annotations

from datetime import datetime

from app.config import TELEMETRY_METRICS, KPI_SVG_VIEWBOX_WIDTH
from app.db import get_con


# ── Column list derived from config — single source of truth ─────────────
# Order matches TELEMETRY_METRICS group/metric order; used as dict keys
# throughout. DO NOT reorder — playback.js telemetry_meta is built from
# the same config iteration and must stay in sync.

_COLUMNS: list[str] = [
    m["column"]
    for metrics in TELEMETRY_METRICS.values()
    for m in metrics
]

# ── Shared SELECT body — both queries use the same join ───────────────────
# v_kinematics  : speed, escape vel, radial vel, C3, Earth grav, rg, lt
# v_earth_moon  : Moon grav, dominance ratio, Moon distance
# orion_elements: eccentricity, inclination
#
# All three share the orion_trajectory datetime_utc spine 1:1.

_SELECT = """
    SELECT
        k.datetime_utc,
        k.speed_kms,
        k.v_escape_kms,
        k.rr_kms,
        k.c3_km2s2,
        k.grav_earth_ms2,
        k.rg_km,
        k.lt_sec,
        em.grav_moon_ms2,
        em.dominance_ratio,
        em.r_moon_km,
        oe.ec,
        oe.inc_deg
    FROM v_kinematics k
    JOIN v_earth_moon   em ON k.datetime_utc = em.datetime_utc
    JOIN orion_elements oe ON k.datetime_utc = oe.datetime_utc
"""

_PRELOAD_SQL = _SELECT + "ORDER BY k.datetime_utc"

_POINT_SQL   = _SELECT + """
    WHERE k.datetime_utc <= ?
    ORDER BY k.datetime_utc DESC
    LIMIT 1
"""

# ── Module-level cache ────────────────────────────────────────────────────
_cache: dict[str, list] | None = None


def get_telemetry_preload() -> dict[str, list]:
    """
    Full-mission telemetry series for all 12 metrics.

    Returns
    -------
    dict[str, list]
        {column_name: [value, ...]} — one list per metric, 12,836 values each.
        Cached after first call; subsequent calls return the same object.
    """
    global _cache
    if _cache is not None:
        return _cache

    con = get_con()
    df  = con.execute(_PRELOAD_SQL).df()

    _cache = {col: df[col].tolist() for col in _COLUMNS}
    return _cache


def get_telemetry_at(dt_utc: datetime) -> dict[str, float]:
    """
    Nearest telemetry row at or before dt_utc.

    Returns
    -------
    dict[str, float]
        {column_name: value} for all 12 metrics.
        Falls back to 0.0 per column if no row qualifies (shouldn't happen
        in practice — dataset starts before any phase timestamp).
    """
    con = get_con()
    df  = con.execute(_POINT_SQL, [dt_utc]).df()

    if df.empty:
        return {col: 0.0 for col in _COLUMNS}

    row = df.iloc[0]
    return {col: float(row[col]) for col in _COLUMNS}


def get_frame_pct(dt_utc: datetime) -> float:
    """
    SVG x-coordinate (0–KPI_SVG_VIEWBOX_WIDTH) for dt_utc.
    Used to position sparkline needles on server-side tile rebuilds.
    """
    con    = get_con()
    result = con.execute("""
        SELECT
            (COUNT(*) FILTER (WHERE datetime_utc <= ?) - 1)::FLOAT
            / NULLIF(COUNT(*) - 1, 0)
            * ?
        FROM orion_trajectory
    """, [dt_utc, KPI_SVG_VIEWBOX_WIDTH]).fetchone()
    return float(result[0]) if result and result[0] is not None else 0.0