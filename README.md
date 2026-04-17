# Artemis II Mission Tracker

A mission control-style dashboard visualizing the Artemis II lunar flyby trajectory
in real time. Built with Python and Dash.

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

## What It Is

An interactive dashboard that animates the Artemis II Orion capsule's 9-day trajectory using high-fidelity ephemeris data from JPL Horizons. The primary visual is a video-style simulation of the Earth–Moon system with the spacecraft position updating over time. Surrounding the simulation is a set of live telemetry tiles covering position, velocity, distances, gravitational forces, and derived orbital mechanics.

---

## Scope

**Mission window:** `2026-Apr-02 01:59 UTC` → `2026-Apr-10 23:54 UTC`

The dataset does not begin at launch. JPL Horizons only has trajectory data for Orion
once DSN ground stations acquired the signal after orbital insertion — approximately
T+3.5 hours after SLS liftoff. The final ~13 minutes of the mission (reentry through
splashdown) are also absent: the plasma sheath surrounding the capsule during atmospheric
reentry blocks all radio communication, cutting off tracking data before the vehicle
reaches Earth's surface.

---

## Stack

| Layer | Technology                      |
|---|---------------------------------|
| Language | Python 3.13+                    |
| Dashboard | Dash (Plotly)                   |
| Data store | DuckDB                          |
| Ephemeris | JPL Horizons REST API           |
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

## Project Structure *(in progress)*

```
Artemis-II-Mission-Tracker/
├── app.py                  # Dash application entry point
├── app/
│   └── config.py           # All constants and paths
├── data/                   # .gitignored / replicable via included scripts.
├── scripts/
```