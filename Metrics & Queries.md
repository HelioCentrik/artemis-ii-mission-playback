# Metrics & Queries — Artemis II Mission Dashboard

All metrics below are derived from raw Horizons data stored in `orion_trajectory` (and, where noted, `moon_trajectory`). Formulas use SI-consistent units unless otherwise noted. All vector operations are in the ICRF geocentric frame.

Constants used throughout:

```python
GM_EARTH = 398_600.4418      # km³/s²  — Earth gravitational parameter
GM_MOON  =   4_902.8001      # km³/s²  — Moon gravitational parameter
GM_SUN   = 1.327_124_4e11    # km³/s²  — Sun gravitational parameter
R_EARTH  =   6_371.0         # km      — Earth mean radius
R_MOON   =   1_737.4         # km      — Moon mean radius
```

---

## 1. Kinematics (from `orion_trajectory` alone)

These require only the Orion state vectors. No secondary bodies needed.

### Speed

The scalar magnitude of the velocity vector.

```
speed = sqrt(vx² + vy² + vz²)   [km/s]
```

Most important single number on the dashboard. Peaks during TLI burn (~10.8 km/s), drops during trans-lunar coast, peaks again during lunar flyby, then rises again during reentry (~11 km/s).

### Earth Distance (Geocentric Range)

Already provided directly as `rg_km`. Also derivable as:

```
r_earth = sqrt(x² + y² + z²)   [km]
```

Both should agree — `rg_km` can serve as a cross-check. Use `rg_km` for display.

### Altitude Above Earth's Surface

```
altitude_earth = r_earth - R_EARTH   [km]
```

Useful for the early mission (LEO parking orbit, TLI) and reentry corridor. Becomes less meaningful during deep trans-lunar coast where "altitude" is a stretch conceptually, but it's still a valid number to display.

### Range Rate (Radial Velocity)

Already provided as `rr_kms`. Negative = closing, positive = receding.

```
rr = (x·vx + y·vy + z·vz) / r_earth   [km/s]
```

Cross-check against `rr_kms`. The sign convention is critical for dashboard labeling — display as "closing" / "receding" rather than raw signed value.

### Transverse (Tangential) Speed

The component of velocity perpendicular to the position vector — i.e., the part of velocity that isn't radial.

```
v_transverse = sqrt(speed² - rr²)   [km/s]
```

Together with range rate, decomposes the velocity vector into "how fast are we moving away from Earth" vs. "how fast are we moving sideways."

---

## 2. Orbital Mechanics (from `orion_trajectory` alone)

### Specific Angular Momentum Vector

```
h = r × v
hx = y·vz - z·vy
hy = z·vx - x·vz
hz = x·vy - y·vx
|h| = sqrt(hx² + hy² + hz²)   [km²/s]
```

The angular momentum vector is perpendicular to the orbital plane. Its magnitude is conserved in a two-body problem. Useful as a sanity check and for computing inclination.

### Orbital Inclination

```
inclination = arccos(hz / |h|)   [degrees]
```

The angle between the orbital plane and Earth's equatorial plane (ICRF equator). Only meaningful during the Earth-orbit and early trans-lunar phases — once the Moon's gravity becomes dominant, "inclination" in a geocentric two-body sense loses physical meaning.

### Specific Orbital Energy (Vis-Viva)

```
ε = (speed² / 2) - (GM_EARTH / r_earth)   [km²/s²]
```

- **ε < 0**: bound to Earth (elliptical orbit)
- **ε = 0**: exactly at escape velocity
- **ε > 0**: hyperbolic — unbound from Earth (trans-lunar coast, deep space)

This is the single cleanest indicator of mission phase. Watching ε cross zero marks the moment Orion escapes Earth's gravitational well.

### Escape Velocity at Current Distance

```
v_escape = sqrt(2 · GM_EARTH / r_earth)   [km/s]
```

The minimum speed required to escape Earth from the current distance. Pair with current speed on the dashboard — when speed > v_escape, the spacecraft is unbound.

### C3 (Characteristic Energy)

```
C3 = 2 · ε = speed² - (2 · GM_EARTH / r_earth)   [km²/s²]
```

C3 is the standard mission design metric for departure energy. C3 = 0 is Earth escape; for a trans-lunar trajectory, C3 is slightly positive (typically ~0.5–2 km²/s² for TLI). Negative C3 means still in a closed Earth orbit.

### Eccentricity Vector (Laplace-Runge-Lenz)

```
e_vec = (v × h) / GM_EARTH - r̂
e = |e_vec|   [dimensionless]
```

where `r̂ = r / |r|` is the unit position vector. Eccentricity describes orbit shape:

- e = 0: circular
- 0 < e < 1: elliptical
- e = 1: parabolic (escape)
- e > 1: hyperbolic

The eccentricity vector points toward periapsis (closest approach to Earth).

### Semi-Major Axis

```
a = -GM_EARTH / (2 · ε)   [km]
```

Only meaningful when ε < 0 (bound orbit). For a hyperbolic trajectory (trans-lunar coast), `a` is negative — this is mathematically valid but display it with a note or hide it once C3 > 0.

---

## 3. Earth–Moon Geometry (requires `moon_trajectory`)

These metrics require the Moon's position vector `(mx, my, mz)` from the planned `moon_trajectory` table, queried at matching timestamps.

### Spacecraft-to-Moon Distance

```
dx = x - mx
dy = y - my
dz = z - mz
r_moon = sqrt(dx² + dy² + dz²)   [km]
```

The primary metric for the lunar flyby. Minimum value of `r_moon` across the mission gives closest approach distance and timestamp.

### Altitude Above Moon's Surface

```
altitude_moon = r_moon - R_MOON   [km]
```

The closest approach altitude above the lunar surface — the most dramatic single number of the flyby phase.

### Spacecraft-to-Moon Range Rate

```
dvx = vx - mvx
dvy = vy - mvy
dvz = vz - mvz
rr_moon = (dx·dvx + dy·dvy + dz·dvz) / r_moon   [km/s]
```

Closing speed relative to the Moon. Negative = approaching, positive = receding.

### Earth–Moon Distance

```
r_em = sqrt(mx² + my² + mz²)   [km]
```

The Earth–Moon range at any given time. Provides context for how far out Orion is relative to the total Earth–Moon distance.

### Fraction of Earth–Moon Distance Traveled

```
fraction = r_earth / r_em   [0 to ~1+]
```

A simple normalized progress metric. Reaches ~1 at lunar closest approach, exceeds 1 briefly if Orion passes beyond the Moon.

---

## 4. Gravitational Accelerations

Gravitational acceleration is the force per unit mass — i.e., the acceleration vector the spacecraft would experience from each body. These are vectors in the ICRF frame.

### From Earth

```
a_earth_vec = -GM_EARTH · (r / r_earth³)
|a_earth| = GM_EARTH / r_earth²   [km/s²  →  convert to mm/s² for display]
```

Dominant during LEO and early trans-lunar coast. Falls off as 1/r².

### From the Moon (requires `moon_trajectory`)

```
a_moon_vec = -GM_MOON · (r_to_moon / r_moon³)
|a_moon| = GM_MOON / r_moon²
```

Becomes significant and eventually dominant as Orion approaches closest approach. The crossover point — where Moon's gravitational pull exceeds Earth's — can be computed and marked as a mission event.

### Earth–Moon Gravitational Crossover

The point at which `|a_moon| > |a_earth|`. This is related to but not identical to the classical Lagrange L1 point or the "sphere of influence" boundary. Worth computing explicitly as a labeled event on the trajectory.

```
Crossover when:  GM_MOON / r_moon² = GM_EARTH / r_earth²
```

### From the Sun _(approximate)_

The Sun's position relative to Earth can be obtained by adding a third Horizons query (body `10`, Sun, same window), or approximated from the Earth's known heliocentric orbit. Sun's gravitational influence on Orion is small relative to Earth and Moon during this mission but non-trivial for high-precision work.

```
a_sun_vec = -GM_SUN · (r_to_sun / r_sun³)
```

Primarily useful as a visualization element (show the Sun's pull direction) rather than a metric the viewer needs to read precisely.

### Net Gravitational Acceleration Vector

```
a_net = a_earth_vec + a_moon_vec + a_sun_vec
|a_net| = magnitude of combined acceleration
```

The direction of `a_net` relative to the spacecraft velocity vector determines whether Orion is accelerating or decelerating — and is the fundamental driver of the trajectory's shape.

---

## 5. Additional Telemetry (from raw data)

These are direct re-expressions of raw columns, formatted for display.

| Metric               | Source                         | Notes                                                                      |
| -------------------- | ------------------------------ | -------------------------------------------------------------------------- |
| Light time           | `lt_sec`                       | One-way signal delay from Earth geocenter. Divide by 60 for minutes.       |
| Range rate           | `rr_kms`                       | Already in km/s. Display as positive/negative with closing/receding label. |
| Mission elapsed time | `datetime_utc - mission_start` | Seconds or D+HH:MM:SS format                                               |
| Mission phase        | Derived from range thresholds  | LEO / TLI coast / Lunar approach / Flyby / Return coast / Reentry          |

---

## 6. Orbital Elements from Horizons (`orion_elements`)

A dedicated Horizons fetch using `EPHEM_TYPE=ELEMENTS` for the same spacecraft and
window returns pre-computed osculating elements at each timestep. These are sourced
directly from JPL's full n-body solution and serve as ground truth for the dashboard's
orbital mechanics panel — more precise than the two-body derivations in Section 2.

| Element | Column | Units | Notes |
|---|---|---|---|
| Eccentricity | `ec` | — | < 1 = elliptical, > 1 = hyperbolic |
| Semi-major axis | `a_km` | km | Negative for hyperbolic; hide or note when `ec > 1` |
| Inclination | `inc_deg` | degrees | Relative to ICRF equatorial plane |
| Longitude of ascending node | `om_deg` | degrees | Ω |
| Argument of periapsis | `w_deg` | degrees | ω |
| True anomaly | `ta_deg` | degrees | ν — current position in orbit |
| Periapsis distance | `qr_km` | km | Closest approach to Earth |
| Apoapsis distance | `ad_km` | km | Only meaningful when `ec < 1` |
| Orbital period | `pr_d` | days | Only meaningful when `ec < 1` |

These columns supersede the equivalent two-body derivations in Section 2 wherever
precision matters. The Section 2 formulas remain useful for any metric not covered by
the ELEMENTS output (e.g., specific orbital energy ε, C3, gravitational accelerations).

---

## Notes on Approximation

Several of the formulas above use **two-body (Keplerian) approximations** — meaning they treat Earth (or Moon) as the only gravitational influence. The actual Orion trajectory is an n-body solution accounting for Earth, Moon, Sun, and higher-order perturbations (Earth's oblateness, etc.).

This means:

- Metrics like eccentricity, semi-major axis, and orbital energy will drift slowly during trans-lunar coast even though they'd be conserved in a pure two-body problem.
- These drifts are physically real and reflect the actual multi-body dynamics.
- For a visualization dashboard, the approximations are accurate enough — the numbers are interesting and correct in order of magnitude. For navigation-grade computation, use the Horizons ELEMENTS output directly.