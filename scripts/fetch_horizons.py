# scripts/fetch_horizons.py
#
# Generic JPL Horizons client. Handles both VECTORS and ELEMENTS ephemeris types.
# Called by init_db.py with a query config dict — not intended to be run directly,
# though each QUERY_CONFIG can be tested standalone via __main__.

import sys
from pathlib import Path

import requests
import pandas as pd
from dateutil import parser as dateutil_parser

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import (
    HORIZONS_URL,
    SPACECRAFT_ID, MOON_ID, SUN_ID,
    EPHEM_START, EPHEM_STOP, STEP_SIZE,
    CENTER, REF_SYSTEM, REF_PLANE,
    OUT_UNITS, VEC_TABLE,
    TABLE_TRAJECTORY, TABLE_ELEMENTS, TABLE_MOON, TABLE_SUN,
)

# ---------------------------------------------------------------------------
# Column schemas — positional, matching Horizons CSV output with VEC_LABELS=NO
# ---------------------------------------------------------------------------

VECTOR_COLUMNS = [
    "jd_tdb", "datetime_str",
    "x_km", "y_km", "z_km",
    "vx_kms", "vy_kms", "vz_kms",
    "lt_sec", "rg_km", "rr_kms",
]
VECTOR_NUMERIC = [
    "x_km", "y_km", "z_km",
    "vx_kms", "vy_kms", "vz_kms",
    "lt_sec", "rg_km", "rr_kms",
]

ELEMENTS_COLUMNS = [
    "jd_tdb", "datetime_str",
    "ec", "qr_km", "inc_deg", "om_deg", "w_deg",
    "tp_jd", "n_deg_d", "ma_deg", "ta_deg",
    "a_km", "ad_km", "pr_d",
]
ELEMENTS_NUMERIC = [
    "ec", "qr_km", "inc_deg", "om_deg", "w_deg",
    "tp_jd", "n_deg_d", "ma_deg", "ta_deg",
    "a_km", "ad_km", "pr_d",
]

# ---------------------------------------------------------------------------
# Query configs — one entry per table. This is the only place body/type varies.
# ---------------------------------------------------------------------------

QUERY_CONFIGS = [
    {
        "table":      TABLE_TRAJECTORY,
        "label":      "Orion state vectors",
        "command":    SPACECRAFT_ID,
        "ephem_type": "VECTORS",
    },
    {
        "table":      TABLE_ELEMENTS,
        "label":      "Orion orbital elements",
        "command":    SPACECRAFT_ID,
        "ephem_type": "ELEMENTS",
    },
    {
        "table":      TABLE_MOON,
        "label":      "Moon state vectors",
        "command":    MOON_ID,
        "ephem_type": "VECTORS",
    },
    {
        "table":      TABLE_SUN,
        "label":      "Sun state vectors (geocentric)",
        "command":    SUN_ID,
        "ephem_type": "VECTORS",
    },
]

# ---------------------------------------------------------------------------
# Core client
# ---------------------------------------------------------------------------

def _build_params(command: str, ephem_type: str) -> dict:
    base = {
        "format":     "json",
        "COMMAND":    f"'{command}'",
        "OBJ_DATA":   "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": ephem_type,
        "CENTER":     f"'{CENTER}'",
        "START_TIME": f"'{EPHEM_START}'",
        "STOP_TIME":  f"'{EPHEM_STOP}'",
        "STEP_SIZE":  f"'{STEP_SIZE}'",
        "CSV_FORMAT": "YES",
        "REF_PLANE":  REF_PLANE,
        "REF_SYSTEM": REF_SYSTEM,
    }
    if ephem_type == "VECTORS":
        base["VEC_TABLE"]  = VEC_TABLE
        base["VEC_LABELS"] = "NO"
        base["OUT_UNITS"]  = OUT_UNITS
    return base


def _fetch_raw(command: str, ephem_type: str, label: str) -> str:
    print(f"  Querying Horizons — {label}...")
    response = requests.get(
        HORIZONS_URL,
        params=_build_params(command, ephem_type),
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Horizons API error: {data['error']}")

    result = data.get("result", "")
    if "$$SOE" not in result:
        print("\n--- Horizons raw response (no data block) ---")
        print(result[:1000])
        raise RuntimeError(
            f"No ephemeris data block returned for {label}. "
            "Check COMMAND and query window."
        )

    return result


def _extract_block(raw: str) -> list[list[str]]:
    """Pull rows between $$SOE / $$EOE markers and split into field lists."""
    soe = raw.index("$$SOE") + len("$$SOE")
    eoe = raw.index("$$EOE")
    block = raw[soe:eoe].strip()

    rows = []
    for line in block.splitlines():
        line = line.strip().rstrip(",")
        if not line:
            continue
        rows.append([p.strip() for p in line.split(",")])
    return rows


def _parse_datetime(series: pd.Series) -> pd.Series:
    return (
        series
        .str.replace(r"^A\.D\.\s*", "", regex=True)
        .apply(dateutil_parser.parse)
    )


def parse_vectors(raw: str) -> pd.DataFrame:
    rows = _extract_block(raw)
    rows = [r for r in rows if len(r) >= len(VECTOR_COLUMNS)]
    df = pd.DataFrame([r[:len(VECTOR_COLUMNS)] for r in rows], columns=VECTOR_COLUMNS)

    df["jd_tdb"]      = pd.to_numeric(df["jd_tdb"])
    df["datetime_utc"] = _parse_datetime(df["datetime_str"])
    df[VECTOR_NUMERIC] = df[VECTOR_NUMERIC].apply(pd.to_numeric)

    df = df.drop(columns=["datetime_str"])
    return df[["datetime_utc", "jd_tdb"] + VECTOR_NUMERIC]


def parse_elements(raw: str) -> pd.DataFrame:
    rows = _extract_block(raw)
    rows = [r for r in rows if len(r) >= len(ELEMENTS_COLUMNS)]
    sentinel_cols = ["ad_km", "pr_d"]
    normal_cols = [c for c in ELEMENTS_NUMERIC if c not in sentinel_cols]

    df = pd.DataFrame([r[:len(ELEMENTS_COLUMNS)] for r in rows], columns=ELEMENTS_COLUMNS)
    df["jd_tdb"]       = pd.to_numeric(df["jd_tdb"])
    df["datetime_utc"] = _parse_datetime(df["datetime_str"])
    df[normal_cols] = df[normal_cols].apply(pd.to_numeric)
    df[sentinel_cols] = df[sentinel_cols].apply(pd.to_numeric, errors="coerce")
    df = df.drop(columns=["datetime_str"])

    return df[["datetime_utc", "jd_tdb"] + ELEMENTS_NUMERIC]


def fetch(config: dict) -> pd.DataFrame:
    raw = _fetch_raw(config["command"], config["ephem_type"], config["label"])

    if config["ephem_type"] == "VECTORS":
        df = parse_vectors(raw)
    elif config["ephem_type"] == "ELEMENTS":
        df = parse_elements(raw)
    else:
        raise ValueError(f"Unknown ephem_type: {config['ephem_type']}")

    print(f"    Parsed {len(df):,} rows  "
          f"({df['datetime_utc'].iloc[0]}  →  {df['datetime_utc'].iloc[-1]})")
    return df


# ---------------------------------------------------------------------------
# Standalone test — run any config directly
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    names = {c["table"]: c for c in QUERY_CONFIGS}
    parser = argparse.ArgumentParser(description="Test a single Horizons fetch.")
    parser.add_argument(
        "table",
        choices=list(names.keys()),
        help="Which config to test",
    )
    args = parser.parse_args()

    cfg = names[args.table]
    df = fetch(cfg)
    print("\n--- Sample (head) ---")
    print(df.head().to_string(index=False))
    print("\n--- dtypes ---")
    print(df.dtypes)