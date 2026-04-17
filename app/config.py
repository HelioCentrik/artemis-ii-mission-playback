# app/config.py

from pathlib import Path

# --- Project Paths ---
ROOT_DIR  = Path(__file__).parent
DATA_DIR  = ROOT_DIR / "data"
DB_PATH   = DATA_DIR / "artemis2.duckdb"

# --- Horizons API ---
HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

# --- Spacecraft & Bodies ---
SPACECRAFT_ID = "-1024"   # Orion capsule (Artemis II)
MOON_ID       = "301"     # Moon
SUN_ID        = "10"      # Sun

# --- Query Window ---
MISSION_START = "2026-Apr-02 01:59"
MISSION_STOP  = "2026-Apr-10 23:54"
STEP_SIZE     = "1m"

# --- Reference Frame ---
CENTER     = "500@399"    # Geocenter (Earth-centered)
REF_SYSTEM = "ICRF"
REF_PLANE  = "FRAME"

# --- Output Units ---
OUT_UNITS = "KM-S"        # km and km/s
VEC_TABLE = "3"           # Position + velocity + light time + range + range rate

# --- Database Tables ---
TABLE_TRAJECTORY = "orion_trajectory"
TABLE_ELEMENTS   = "orion_elements"
TABLE_MOON       = "moon_trajectory"
TABLE_SUN        = "sun_trajectory"

# --- Validation ---
EXPECTED_ROW_COUNT = 12_836