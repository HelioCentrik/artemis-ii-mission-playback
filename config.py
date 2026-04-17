# config.py

from pathlib import Path

# --- Project Paths ---
ROOT_DIR   = Path(__file__).parent
DATA_DIR   = ROOT_DIR / "data"
DB_PATH    = DATA_DIR / "artemis2.duckdb"

# --- Horizons API ---
HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
VEC_TABLE = "3"

# --- Spacecraft ---
SPACECRAFT_ID = "-1024"          # Orion capsule (Artemis II)

# --- Query Window ---
MISSION_START = "2026-Apr-02 01:59"
MISSION_STOP = "2026-Apr-10 23:54"
STEP_SIZE     = "1m"             # 1-minute intervals

# --- Reference Frame ---
CENTER        = "500@399"        # Geocenter (Earth-centered)
REF_SYSTEM    = "ICRF"
REF_PLANE     = "FRAME"

# --- Output Units ---
OUT_UNITS     = "KM-S"           # km and km/s

# --- Database ---
TABLE_TRAJECTORY = "orion_trajectory"