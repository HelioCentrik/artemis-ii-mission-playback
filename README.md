# Artemis II • Mission Playback

A mission control-style visualization of the Artemis II lunar flyby trajectory.

**Live:** [artemis-ii-mission.deanallton.com](https://artemis-ii-mission.deanallton.com)

![Dashboard screenshot](assets/artemis-ii.png)

---

## Mission Playback

A two-page web app built around NASA JPL ephemeris data from the Artemis II mission.

**Landing page (`/`)** — Mission overview with crew profiles, launch and splashdown
videos, and a mission image carousel. An IGNITION button navigates to the dashboard.

**Mission playback (`/playback`)** — Animates Orion's 9-day Earth-Moon-Earth
trajectory at 3600× speed (1 hour per second), driven by 12,836 state vectors at
1-minute resolution.

### Controls

| Control | Effect |
|---|---|
| Play / Pause | Starts and pauses the trajectory animation |
| Restart (↺) | Resets playback to the beginning of the dataset |
| Phase scrubber | Seeks to any point in the mission; six named phases with click-to-jump |

### Panels

**Trajectory** — 2D Earth-Moon plane view of Orion's geocentric path. A 24-hour
lookahead arc fades over six hours. Phase event markers are drawn along the arc.

**Telemetry** — Twelve KPI tiles updating each playback frame. Tile types include
sparklines (altitude, speed, acceleration), bar and bidirectional bar gauges
(gravitational accelerations, angular rates), dials, and static readouts. Each tile
pulls from a DuckDB view over the preloaded state vector dataset.

### Mission Window

`2026-Apr-02 01:59 UTC` → `2026-Apr-10 23:54 UTC`

The dataset opens approximately T+3.5 hours after SLS liftoff (DSN acquisition
delay) and ends ~13 minutes before splashdown (reentry plasma blackout). Both gaps
are unresolvable from the Horizons source.

---

## Documentation

**[Data Dictionary](artemis-ii-mission.deanallton.com/docs/Data_Dictionary.html)** — Schema reference: all tables,
fields, coordinate frames, units, and known data gaps (DSN acquisition delay,
reentry blackout).

**[Metrics & Queries](artemis-ii-mission.deanallton.com/docs/Metrics_and_Queries.html)** — Derived metric formulas,
physical constants, and the full SQL query cookbook. Covers kinematics, orbital
mechanics, Earth-Moon geometry, and gravitational accelerations.

---

## Setup

```bash
git clone https://github.com/HelioCentrik/artemis-ii-mission-playback
cd artemis-ii-mission-playback
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Open `http://127.0.0.1:8050`.

> The database (`data/artemis2.duckdb`) is included in the repo — no build step
> required. To rebuild from JPL Horizons, run `python scripts/init_db.py`.

---

## Deployment

```bash
pip install gunicorn gevent
gunicorn main:server \
  --workers 2 \
  --worker-class gevent \
  --worker-connections 50 \
  --timeout 120 \
  --bind 0.0.0.0:8051
```

Gevent async workers are required — the default sync worker serialises concurrent
video requests on the home page. The live demo runs behind a Cloudflare tunnel on a
self-hosted Linux server as a systemd service.

---

## Project Structure

```
pages/       Page modules — landing page (/) and mission playback (/playback/)
app/         Config, data layer, DB singleton, phase detection, telemetry
assets/      CSS, clientside JS (playback engine, home carousel, resize handler)
components/  Reusable Dash layout components — header, scrubber, panels
viz/         Figure builders — trajectory viz, KPI tiles, sparklines
scripts/     Horizons client, DB init, validation probes
main.py      Entrypoint — imports pages, exposes server for Gunicorn
```

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13+ |
| Dashboard | Dash (Plotly) |
| Data store | DuckDB |
| Ephemeris | JPL Horizons REST API |
| Visualization | Plotly (scatter, animations) |

---

## Data & Attribution

**Ephemeris data** — NASA Jet Propulsion Laboratory, [JPL Horizons REST API](https://ssd.jpl.nasa.gov/api/horizons.api). State vectors and osculating orbital elements at 1-minute resolution.

| Object | Horizons ID |
|---|---|
| Orion spacecraft (Artemis II) | `-1024` |
| Moon | `301` |
| Sun | `10` |

**Mission media** — NASA. Crew portraits, launch, and mission photography via [NASA Image and Video Library](https://images.nasa.gov). Launch video via NASA. Recovery video courtesy of Reid Wiseman via [Instagram](https://www.instagram.com/astroreid).