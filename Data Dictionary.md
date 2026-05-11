# Data Dictionary — Artemis II Mission Dashboard

## Primary Source: JPL Horizons REST API

**Provider:** NASA Jet Propulsion Laboratory (JPL) Solar System Dynamics Group **Endpoint:** `https://ssd.jpl.nasa.gov/api/horizons.api` **Documentation:** https://ssd.jpl.nasa.gov/horizons/manual.html

JPL Horizons is the authoritative source for solar system ephemeris data. It provides high-precision position and velocity vectors for spacecraft, planets, moons, asteroids, and comets derived from JPL's integrated dynamical models. For active spacecraft like Orion, trajectory data is reconstructed from Deep Space Network (DSN) tracking solutions and updated throughout the mission.

---

## Data Pipeline

```
JPL Horizons API
      │
      ▼
scripts/fetch_horizons.py   ← pulls raw ephemeris (VECTORS or ELEMENTS)
      │
      ▼
scripts/init_db.py          ← parses, validates, writes to DuckDB
      │
      ▼
data/artemis2.duckdb        ← four tables, 12,836 rows each
      │
      ▼
app/db.py                   ← loads all tables into in-memory DuckDB at startup
      │
      ▼
app/sql.py                  ← creates derived metric views on the in-memory connection
```

Four tables in `artemis2.duckdb`:

|Table|COMMAND|EPHEM_TYPE|Rows|
|---|---|---|---|
|`orion_trajectory`|`-1024`|`VECTORS`|12,836|
|`orion_elements`|`-1024`|`ELEMENTS`|12,836|
|`moon_trajectory`|`301`|`VECTORS`|12,836|
|`sun_trajectory`|`10`|`VECTORS`|12,836|

All tables share the same timestamp spine: `2026-04-02 01:59 UTC` → `2026-04-10 23:54 UTC`, 1-minute step size, ICRF geocentric frame.

---

## Dataset 1 — Orion Capsule Trajectory

### Query Parameters

| Parameter    | Value                   | Notes                                                 |
| ------------ | ----------------------- | ----------------------------------------------------- |
| `COMMAND`    | `-1024`                 | Orion spacecraft (Artemis II)                         |
| `EPHEM_TYPE` | `VECTORS`               | Cartesian state vectors (position + velocity)         |
| `CENTER`     | `500@399`               | Earth geocenter as origin                             |
| `REF_SYSTEM` | `ICRF`                  | International Celestial Reference Frame               |
| `REF_PLANE`  | `FRAME`                 | XY plane aligned to ICRF (equatorial)                 |
| `OUT_UNITS`  | `KM-S`                  | Kilometers and km/s                                   |
| `VEC_TABLE`  | `3`                     | Position + velocity + light time + range + range rate |
| `STEP_SIZE`  | `1m`                    | 1-minute intervals                                    |
| `START_TIME` | `2026-Apr-02 01:59` UTC | First available post-launch tracking point            |
| `STOP_TIME`  | `2026-Apr-10 23:54` UTC | Final point before reentry plasma blackout            |
| `CSV_FORMAT` | `YES`                   | Comma-separated output for deterministic parsing      |
| `VEC_LABELS` | `NO`                    | Labels suppressed; columns parsed positionally        |

### Why These Parameters

**`VECTORS` ephemeris type** gives Cartesian state vectors (X, Y, Z, Vx, Vy, Vz) in a fixed inertial frame. This is the natural representation for computing derived physics — range, speed, orbital energy, closest approach — without angular ambiguity.

**`500@399` (Earth geocenter)** sets the coordinate origin at Earth's center of mass. This makes the dashboard's primary reference frame Earth-relative, which is the most intuitive frame for visualizing launch, TLI, lunar flyby, and reentry from a mission control perspective. All X/Y/Z values are Earth-centered distances in km.

**ICRF / `FRAME` plane** uses the International Celestial Reference Frame — a fixed, non-rotating inertial frame tied to distant quasars. Choosing `REF_PLANE=FRAME` means the Z-axis is aligned to the ICRF pole (close to Earth's north celestial pole), not the ecliptic. This is the standard for spacecraft navigation and keeps the reference frame stable regardless of Earth's orbital position.

**`VEC_TABLE=3`** includes all five output columns beyond the calendar/JD timestamps: position, velocity, light time, range, and range rate. This is the maximum useful set without redundant or derived columns. Light time (`lt_sec`) and range rate (`rr_kms`) are particularly useful for simulating DSN tracking observables in the dashboard.

**1-minute step size** gives ~12,800 rows across the ~9-day mission window — fine-grained enough to resolve events like TLI, lunar closest approach, and reentry corridor accurately, without the dataset size becoming unmanageable.

### Output Schema

Stored in DuckDB table `orion_trajectory`. **12,836 rows, zero nulls.**

|Column|Type|Units|Description|
|---|---|---|---|
|`datetime_utc`|TIMESTAMP|—|Calendar date/time, UTC|
|`jd_tdb`|DOUBLE|days|Julian Date in Barycentric Dynamical Time (TDB)|
|`x_km`|DOUBLE|km|X position, Earth geocenter, ICRF|
|`y_km`|DOUBLE|km|Y position, Earth geocenter, ICRF|
|`z_km`|DOUBLE|km|Z position, Earth geocenter, ICRF|
|`vx_kms`|DOUBLE|km/s|X velocity component|
|`vy_kms`|DOUBLE|km/s|Y velocity component|
|`vz_kms`|DOUBLE|km/s|Z velocity component|
|`lt_sec`|DOUBLE|seconds|One-way light time from observer to spacecraft|
|`rg_km`|DOUBLE|km|Range (distance) from observer to spacecraft|
|`rr_kms`|DOUBLE|km/s|Range rate (radial velocity); negative = closing|

> **Note on `jd_tdb` vs `datetime_utc`:** Horizons returns calendar timestamps in UTC but Julian Dates in TDB (Barycentric Dynamical Time). The difference is small (~65 seconds) and negligible for visualization, but matters for any precision physics computation involving relativistic corrections. Use `datetime_utc` for display and time-axis labeling; use `jd_tdb` if computing against other Horizons-sourced ephemerides (e.g., Moon position), since both will share the same TDB epoch.

---

## Dataset 2 — Orion Orbital Elements

Same query window and spacecraft as Dataset 1, with `EPHEM_TYPE=ELEMENTS`. Horizons
computes osculating orbital elements at each timestep using its full n-body solution —
more precise than deriving them manually from the state vectors.

### Query Parameters

| Parameter | Value | Notes |
|---|---|---|
| `COMMAND` | `-1024` | Orion spacecraft (Artemis II) |
| `EPHEM_TYPE` | `ELEMENTS` | Osculating Keplerian orbital elements |
| `CENTER` | `500@399` | Earth geocenter |
| `REF_SYSTEM` | `ICRF` | |
| `REF_PLANE` | `FRAME` | |
| `START_TIME` | `2026-Apr-02 01:59` UTC | |
| `STOP_TIME` | `2026-Apr-10 23:54` UTC | |
| `STEP_SIZE` | `1m` | |
| `CSV_FORMAT` | `YES` | |

### Output Schema

Stored in DuckDB table `orion_elements`. Expected ~12,836 rows, matching `orion_trajectory` 1:1 on `datetime_utc`.

| Column | Type | Units | Description |
|---|---|---|---|
| `datetime_utc` | TIMESTAMP | — | Calendar date/time, UTC |
| `jd_tdb` | DOUBLE | days | Julian Date, TDB |
| `ec` | DOUBLE | — | Eccentricity |
| `qr_km` | DOUBLE | km | Periapsis distance (closest approach to Earth) |
| `inc_deg` | DOUBLE | degrees | Inclination relative to ICRF equatorial plane |
| `om_deg` | DOUBLE | degrees | Longitude of ascending node (Ω) |
| `w_deg` | DOUBLE | degrees | Argument of periapsis (ω) |
| `tp_jd` | DOUBLE | days | Time of periapsis passage (Julian Date, TDB) |
| `n_deg_d` | DOUBLE | deg/day | Mean motion |
| `ma_deg` | DOUBLE | degrees | Mean anomaly |
| `ta_deg` | DOUBLE | degrees | True anomaly (ν) — current position in orbit |
| `a_km` | DOUBLE | km | Semi-major axis |
| `ad_km` | DOUBLE | km | Apoapsis distance (farthest point from Earth) |
| `pr_d` | DOUBLE | days | Orbital period |

> **Hyperbolic caveat:** Once Orion is on a trans-lunar trajectory (eccentricity > 1),
> apoapsis (`ad_km`) and orbital period (`pr_d`) are physically undefined — there is no
> farthest point and no closed orbit. Horizons returns sentinel values for these columns
> during hyperbolic phases. Filter on `ec < 1` before using `ad_km` or `pr_d`.

---

## Dataset 3 — Moon Position

Same query parameters as Dataset 1, with the following changes:

|Parameter|Value|
|---|---|
|`COMMAND`|`301` (Moon)|
|Table name|`moon_trajectory` _(TBD)_|

Moon position vectors in the same ICRF/geocenter frame allow the dashboard to render the Earth–Moon geometry at any mission timestamp, compute spacecraft-to-Moon range, and identify the closest approach point during the lunar flyby.

---

## Known Data Limitations

### Launch Through ~T+3.5 Hours — No Pre-Tracking Data

The dataset begins at `2026-Apr-02 01:59 UTC`. The SLS launch, ascent, and early trans-lunar injection (TLI) burn are not covered. Horizons does not provide trajectory data for Orion prior to initial DSN acquisition of signal after orbital insertion. The first row in `orion_trajectory` represents the earliest point at which JPL had a reconstructed tracking solution available.

**Dashboard implication:** The trajectory does not begin at Kennedy Space Center or at the launch pad. The earliest visualizable position is already in Earth orbit or early trans-lunar coast.

### Final ~13 Minutes — Reentry Plasma Blackout

The dataset ends at `2026-Apr-10 23:54 UTC`. During atmospheric reentry, the plasma sheath surrounding the capsule blocks all radio communication, including DSN tracking. There is no trajectory data for the reentry corridor from approximately Entry Interface (EI) through splashdown.

**Dashboard implication:** The trajectory terminates before reaching Earth's surface. The endpoint should be labeled clearly as "Last Known Position" or similar — not as splashdown.

### Ephemeris Is a Reconstruction, Not a Prediction

For future or real-time missions, Horizons data reflects JPL's best current trajectory reconstruction based on available DSN tracking. Early in the mission, the solution is updated as additional tracking data is incorporated. Data fetched at different times during the mission may differ slightly for overlapping windows.

### Coordinate Frame Is Inertial, Not Earth-Fixed

ICRF is a non-rotating frame. Earth rotates inside it. X/Y/Z coordinates are **not** tied to geographic features — a spacecraft directly over New York will not have a constant X/Y position as time passes. Converting to geographic coordinates (latitude, longitude, altitude) requires accounting for Earth's rotation (GAST/GMST).

---

## Reproducing the Dataset

```python
# config.py values used for this dataset
SPACECRAFT_ID = "-1024"
MISSION_START = "2026-Apr-02 01:59"
MISSION_STOP  = "2026-Apr-10 23:54"
STEP_SIZE     = "1m"
CENTER        = "500@399"
REF_SYSTEM    = "ICRF"
REF_PLANE     = "FRAME"
OUT_UNITS     = "KM-S"
VEC_TABLE     = "3"
```

Run `scripts/init_db.py` to re-fetch from Horizons and rebuild `artemis2.duckdb` from scratch. Note that re-fetching late in or after the mission may return a slightly updated trajectory solution if JPL has refined their tracking reconstruction.