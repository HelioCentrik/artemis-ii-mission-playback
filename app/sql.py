# app/sql.py
#
# Derived metric view definitions for the in-memory DuckDB connection.
# Call create_views(con) once after the tables are loaded (done by db.py).
# All formulas sourced from Metrics & Queries.md.
#
# Constants embedded as literals to keep SQL self-contained; canonical values
# live in config.py and are cross-referenced here in comments.

# ── Physical constants (from config.py / Metrics & Queries.md) ──────────
# GM_EARTH = 398_600.4418  km³/s²
# GM_MOON  =   4_902.8001  km³/s²
# R_EARTH  =   6_371.0     km
# R_MOON   =   1_737.4     km


_V_KINEMATICS = """
CREATE OR REPLACE VIEW v_kinematics AS
WITH base AS (
    SELECT
        datetime_utc,
        jd_tdb,
        x_km, y_km, z_km,
        vx_kms, vy_kms, vz_kms,
        rg_km,
        rr_kms,
        lt_sec,

        -- Pre-compute intermediates used by multiple derived columns
        vx_kms * vx_kms + vy_kms * vy_kms + vz_kms * vz_kms  AS speed_sq,

        -- Angular momentum vector components: h = r × v
        y_km * vz_kms - z_km * vy_kms  AS hx,
        z_km * vx_kms - x_km * vz_kms  AS hy,
        x_km * vy_kms - y_km * vx_kms  AS hz

    FROM orion_trajectory
)
SELECT
    datetime_utc,
    jd_tdb,
    x_km, y_km, z_km,
    vx_kms, vy_kms, vz_kms,
    rg_km,
    rr_kms,
    lt_sec,

    -- Speed (scalar velocity magnitude)                         km/s
    SQRT(speed_sq)                                                  AS speed_kms,

    -- Altitude above Earth's surface                            km
    rg_km - 6371.0                                                  AS alt_earth_km,

    -- Transverse (tangential) speed: sqrt(|v|² - rr²)           km/s
    -- GREATEST guard prevents sqrt of tiny negative float noise
    SQRT(GREATEST(speed_sq - rr_kms * rr_kms, 0.0))                AS v_transverse_kms,

    -- Escape velocity at current distance: sqrt(2·GM/r)         km/s
    SQRT(2.0 * 398600.4418 / rg_km)                                 AS v_escape_kms,

    -- Specific orbital energy: ε = speed²/2 − GM/r             km²/s²
    speed_sq / 2.0 - 398600.4418 / rg_km                           AS epsilon_km2s2,

    -- Characteristic energy: C3 = 2ε = speed² − 2·GM/r        km²/s²
    speed_sq - 2.0 * 398600.4418 / rg_km                           AS c3_km2s2,

    -- Gravitational acceleration from Earth                     m/s²
    -- GM/r² [km/s²] × 1000 → m/s²
    (398600.4418 / (rg_km * rg_km)) * 1000.0                       AS grav_earth_ms2,

    -- Angular momentum components                               km²/s
    hx  AS hx_km2s,
    hy  AS hy_km2s,
    hz  AS hz_km2s,

    -- |h| magnitude                                             km²/s
    SQRT(hx * hx + hy * hy + hz * hz)                              AS h_km2s,

    -- Inclination (geocentric two-body approx)                  degrees
    -- Only meaningful during early mission; loses sense during lunar SOI
    DEGREES(ACOS(LEAST(GREATEST(
        hz / NULLIF(SQRT(hx * hx + hy * hy + hz * hz), 0.0),
        -1.0
    ), 1.0)))                                                        AS inclination_deg

FROM base
"""


_V_EARTH_MOON = """
CREATE OR REPLACE VIEW v_earth_moon AS
WITH base AS (
    SELECT
        o.datetime_utc,

        -- Relative position vector (spacecraft − Moon)
        o.x_km  - m.x_km   AS dx,
        o.y_km  - m.y_km   AS dy,
        o.z_km  - m.z_km   AS dz,

        -- Relative velocity vector
        o.vx_kms - m.vx_kms  AS dvx,
        o.vy_kms - m.vy_kms  AS dvy,
        o.vz_kms - m.vz_kms  AS dvz,

        -- Earth–Moon distance: |Moon position vector|
        SQRT(m.x_km * m.x_km + m.y_km * m.y_km + m.z_km * m.z_km)  AS r_em_km,

        -- Pass-through for trajectory viz
        o.x_km  AS o_x_km,  o.y_km  AS o_y_km,  o.z_km  AS o_z_km,
        m.x_km  AS m_x_km,  m.y_km  AS m_y_km,  m.z_km  AS m_z_km

    FROM orion_trajectory o
    JOIN moon_trajectory  m ON o.datetime_utc = m.datetime_utc
),
with_r AS (
    SELECT
        *,
        SQRT(dx * dx + dy * dy + dz * dz)  AS r_moon_km
    FROM base
)
SELECT
    datetime_utc,

    -- Spacecraft-to-Moon distance                              km
    r_moon_km,

    -- Altitude above lunar surface                            km
    r_moon_km - 1737.4                                              AS alt_moon_km,

    -- Moon-relative range rate: (dr·dv) / |dr|               km/s
    -- Negative = closing on Moon, positive = receding
    (dx * dvx + dy * dvy + dz * dvz) / r_moon_km                   AS rr_moon_kms,

    -- Earth–Moon distance                                     km
    r_em_km,

    -- Fractional progress toward Moon (0 at Earth, ~1 at flyby)
    -- Uses Earth distance from v_kinematics; approximated here as o_x/y/z
    SQRT(o_x_km * o_x_km + o_y_km * o_y_km + o_z_km * o_z_km)
        / NULLIF(r_em_km, 0.0)                                      AS em_fraction,

    -- Gravitational acceleration from Moon                    m/s²
    -- GM/r² [km/s²] × 1000 → m/s²
    (4902.8001 / (r_moon_km * r_moon_km)) * 1000.0                  AS grav_moon_ms2,

    -- Raw positions for trajectory viz
    o_x_km, o_y_km, o_z_km,
    m_x_km, m_y_km, m_z_km

FROM with_r
"""


def create_views(con: "duckdb.DuckDBPyConnection") -> None:
    """Register all derived metric views on the in-memory connection."""
    con.execute(_V_KINEMATICS)
    con.execute(_V_EARTH_MOON)