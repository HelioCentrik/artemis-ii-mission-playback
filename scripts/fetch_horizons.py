# scripts/fetch_horizons.py

import sys
from pathlib import Path

import requests
import pandas as pd
from dateutil import parser as dateutil_parser

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    HORIZONS_URL,
    SPACECRAFT_ID,
    MISSION_START,
    MISSION_STOP,
    STEP_SIZE,
    CENTER,
    REF_SYSTEM,
    REF_PLANE,
    OUT_UNITS,
    VEC_TABLE,
)

# Column order matches VEC_TABLE=2 CSV output exactly
COLUMNS = [
    "jd_tdb",
    "datetime_str",
    "x_km",
    "y_km",
    "z_km",
    "vx_kms",
    "vy_kms",
    "vz_kms",
    "lt_sec",
    "rg_km",
    "rr_kms",
]


def build_params() -> dict:
    return {
        "format":     "json",
        "COMMAND":    f"'{SPACECRAFT_ID}'",
        "OBJ_DATA":   "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "VECTORS",
        "CENTER":     f"'{CENTER}'",
        "START_TIME": f"'{MISSION_START}'",
        "STOP_TIME":  f"'{MISSION_STOP}'",
        "STEP_SIZE":  f"'{STEP_SIZE}'",
        "VEC_TABLE":  VEC_TABLE,
        "VEC_LABELS": "NO",
        "OUT_UNITS":  OUT_UNITS,
        "CSV_FORMAT": "YES",
        "REF_PLANE":  REF_PLANE,
        "REF_SYSTEM": REF_SYSTEM,
    }


def fetch_raw() -> str:
    print("Querying JPL Horizons API...")
    response = requests.get(HORIZONS_URL, params=build_params(), timeout=60)
    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(f"Horizons API error: {data['error']}")

    result = data.get("result", "")

    if "$$SOE" not in result:
        print("\n--- Horizons raw response (no data block found) ---")
        print(result)
        raise RuntimeError(
            "No ephemeris data block in response. "
            "Spacecraft ID may be wrong, or data isn't available for this window."
        )

    return result


def parse_trajectory(raw: str) -> pd.DataFrame:
    print("Parsing trajectory data...")

    soe = raw.index("$$SOE") + len("$$SOE")
    eoe = raw.index("$$EOE")
    block = raw[soe:eoe].strip()

    rows = []
    for line in block.splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 11:
            continue  # skip any malformed lines
        rows.append(parts[:11])

    df = pd.DataFrame(rows, columns=COLUMNS)

    # Julian Date
    df["jd_tdb"] = pd.to_numeric(df["jd_tdb"])

    # Calendar date — strip "A.D. " prefix before parsing
    df["datetime_utc"] = (
        df["datetime_str"]
        .str.replace(r"^A\.D\.\s*", "", regex=True)
        .apply(dateutil_parser.parse)
    )

    # Numeric columns
    numeric_cols = ["x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms",
                    "lt_sec", "rg_km", "rr_kms"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

    # Drop raw string, reorder with datetime first
    df = df.drop(columns=["datetime_str"])
    df = df[["datetime_utc", "jd_tdb"] + numeric_cols]

    print(f"  Parsed {len(df):,} rows")
    print(f"  Range: {df['datetime_utc'].iloc[0]}  →  {df['datetime_utc'].iloc[-1]}")

    return df


def fetch_trajectory() -> pd.DataFrame:
    return parse_trajectory(fetch_raw())


if __name__ == "__main__":
    df = fetch_trajectory()
    print("\n--- Sample ---")
    print(df.head())
    print("\n--- dtypes ---")
    print(df.dtypes)