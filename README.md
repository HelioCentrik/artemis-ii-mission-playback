# Artemis II Mission Tracker

A mission control-style dashboard visualizing the Artemis II lunar flyby trajectory
in real time. Built with Python and Dash.

---

## What It Is

An interactive dashboard that animates the Artemis II Orion capsule's 9-day trajectory
using high-fidelity ephemeris data from JPL Horizons. The primary visual is a video-style
simulation of the Earth–Moon system with the spacecraft position updating over time.
Surrounding the simulation is a set of live telemetry tiles — hot-colored metrics panels
covering position, velocity, distances, gravitational forces, and derived orbital mechanics.

**Color palette:** teal, cobalt, pink, purple. Dark background. Mission control aesthetic.

---

## Scope *(to be expanded)*

- [ ] Video simulation: animated 3D/2D trajectory of Orion, Earth, and Moon
- [ ] Telemetry tiles: speed, Earth distance, Moon distance, range rate, and derived metrics
- [ ] Gravitational force vectors from Earth, Moon, and Sun
- [ ] Orbital mechanics panel: energy, angular momentum, orbital elements
- [ ] Timeline scrubber: step through the mission minute by minute
- [ ] Key event markers: TLI, lunar closest approach, entry interface

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Dashboard | Dash (Plotly) |
| Data store | DuckDB |
| Ephemeris | JPL Horizons REST API |
| Visualization | Plotly (3D scatter, animations) |

---

## Data Pipeline

```
JPL Horizons API
      │
      ▼
scripts/fetch_horizons.py   ← pulls raw trajectory CSV
      │
      ▼
scripts/init_db.py          ← parses and writes to DuckDB
      │
      ▼
data/artemis2.duckdb        ← orion_trajectory table (12,836 rows)
```


---

## Setup

```bash
# Clone and create virtual environment
git clone <repo-url>
cd Artemis-II-Mission-Tracker
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Build the database (fetches from JPL Horizons)
python scripts/init_db.py

# Launch the dashboard
python app.py
```

---

## Project Structure *(in progress)*

```
Artemis-II-Mission-Tracker/
├── app.py                  # Dash application entry point
├── config.py               # All constants and paths
├── requirements.txt
├── data/
│   └── artemis2.duckdb     # gitignored
├── scripts/
│   ├── fetch_horizons.py   # Horizons API client
│   ├── init_db.py          # Database builder
│   └── probe_db.py         # Schema/sanity checks
└── docs/
    ├── DATA_SOURCES.md
    └── DERIVED_METRICS.md
```