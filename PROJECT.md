# Artemis II Mission Playback
### A Mission Control Dashboard

9 days. 12,836 state vectors. One lunar flyby. Visualized at mission control fidelity from real NASA JPL ephemeris data.

**[GitHub](https://github.com/HelioCentrik/artemis-ii-mission-playback)**

---

## What It Shows

Artemis II is NASA's first crewed lunar flyby since Apollo 17 in 1972. Four astronauts aboard the Orion capsule completed a free-return trajectory around the Moon and returned to Earth over nine days in April 2026. This dashboard animates that journey at 3600x speed using the actual tracking data NASA used to navigate the mission.

---

## The Visuals

**Trajectory Panel** - A top-down view of the Earth-Moon system showing Orion's full path. Earth and Moon are rendered as shaded circles with atmospheric glow. The solid arc traces where the capsule has been; a dashed arc shows the return path. Colored event markers appear along the arc at key mission moments, distinguishing propulsive burns (orange) from physics events (silver). A live spacecraft marker updates continuously during playback.

**Phase Scrubber** - A horizontal track at the bottom of the trajectory panel with six clickable phase dots, spaced according to actual mission elapsed time. Clicking any dot jumps the entire dashboard to that phase of the mission. A play/pause button runs real-time animation from any position.

**Telemetry Panels** - Four live data groups update at each phase, all derived from real tracking data:
- **Vectors** - total speed, escape velocity, radial velocity
- **Trajectory / Orbital** - characteristic energy (C3), eccentricity, inclination
- **Gravitational Pull** - Earth and Moon gravitational accelerations
- **Range / Comms** - Earth distance, one-way light time, Moon distance

---

## The Data

The dataset covers `2026-Apr-02 01:59 UTC` through `2026-Apr-10 23:54 UTC` at one-minute resolution. Two gaps exist and are worth knowing about.

The dataset does not begin at launch. JPL Horizons only acquires Orion's trajectory once Deep Space Network ground stations lock signal after orbital insertion, roughly T+3.5 hours after SLS liftoff. The ascent, launch, and early parking orbit are not present in the tracking record.

The dataset does not end at splashdown either. During atmospheric reentry, the plasma sheath surrounding the capsule blocks all radio communication. DSN tracking cuts off at Entry Interface, so the final position in this playback is labeled "Last Available Position", not the ocean.

---

## The Pipeline

Ephemeris data from the JPL Horizons REST API (state vectors + orbital elements for Orion, Moon, and Sun)  
→ validated and ingested at 1-minute resolution across the mission window  
→ DuckDB (four tables sharing a common timestamp spine, with precomputed SQL views for all derived metrics)  
→ in-memory load at startup  
→ clientside animation hot path via Plotly restyle API for real-time playback at 10 fps  
→ Dash/Plotly frontend with a CSS token pipeline for theming. Self-hosted.

---

## Stack

Python · JavaScript · Dash · Plotly · DuckDB

---

## Data & Attribution

**Ephemeris data** - NASA Jet Propulsion Laboratory, [JPL Horizons REST API](https://ssd.jpl.nasa.gov/api/horizons.api). Orion spacecraft ID `-1024`. State vectors and osculating orbital elements at 1-minute resolution.

**Moon and Sun ephemerides** - JPL Horizons, object IDs `301` (Moon) and `10` (Sun), same query window and resolution as Orion.