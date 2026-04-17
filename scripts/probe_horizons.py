# scripts/probe_horizons.py
#
# Probes all four Horizons queries with a small sample window and dumps:
#   - Raw response block (first 3 rows, VEC_LABELS=YES so columns are visible)
#   - Parsed DataFrame sample and dtypes
#   - Sentinel check for non-numeric values that would break pd.to_numeric
#
# Usage:
#   python scripts/probe_horizons.py                 # probe all four
#   python scripts/probe_horizons.py orion_elements  # probe one

import sys
import argparse
from pathlib import Path

import requests
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import (
    HORIZONS_URL,
    CENTER, REF_SYSTEM, REF_PLANE, OUT_UNITS, VEC_TABLE,
)
from scripts.fetch_horizons import QUERY_CONFIGS, parse_vectors, parse_elements

PROBE_START = "2026-Apr-02 02:00"
PROBE_STOP  = "2026-Apr-02 02:09"
PROBE_STEP  = "1m"   # 9 rows


def build_probe_params(command: str, ephem_type: str, vec_labels: str = "NO") -> dict:
    base = {
        "format":     "json",
        "COMMAND":    f"'{command}'",
        "OBJ_DATA":   "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": ephem_type,
        "CENTER":     f"'{CENTER}'",
        "START_TIME": f"'{PROBE_START}'",
        "STOP_TIME":  f"'{PROBE_STOP}'",
        "STEP_SIZE":  f"'{PROBE_STEP}'",
        "CSV_FORMAT": "YES",
        "VEC_LABELS": vec_labels,
        "REF_PLANE":  REF_PLANE,
        "REF_SYSTEM": REF_SYSTEM,
    }
    if ephem_type == "VECTORS":
        base["VEC_TABLE"] = VEC_TABLE
        base["OUT_UNITS"] = OUT_UNITS
    return base


def fetch_raw_probe(command: str, ephem_type: str, vec_labels: str = "NO") -> str:
    response = requests.get(
        HORIZONS_URL,
        params=build_probe_params(command, ephem_type, vec_labels),
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"Horizons error: {data['error']}")

    result = data.get("result", "")
    if "$$SOE" not in result:
        print("  !! No data block returned. Raw response:")
        print(result[:1000])
        return ""

    return result


def check_sentinels(df: pd.DataFrame) -> None:
    found_any = False
    for col in df.columns:
        if col in ("datetime_utc", "jd_tdb"):
            continue
        bad_mask = pd.to_numeric(df[col], errors="coerce").isna()
        bad_vals = df.loc[bad_mask, col].unique()
        if len(bad_vals):
            print(f"  !! SENTINEL — '{col}': {bad_vals}")
            found_any = True
    if not found_any:
        print("  All numeric columns clean.")


def probe(cfg: dict) -> None:
    divider = "=" * 60
    print(f"\n{divider}")
    print(f"  {cfg['label'].upper()}")
    print(f"  table={cfg['table']}  command={cfg['command']}  ephem_type={cfg['ephem_type']}")
    print(divider)

    # --- Raw block with labels so column names are visible ---
    print("\n--- RAW (VEC_LABELS=YES, first 3 lines) ---")
    raw_labeled = fetch_raw_probe(cfg["command"], cfg["ephem_type"], vec_labels="YES")
    if not raw_labeled:
        print("  No data — skipping.")
        return

    soe = raw_labeled.index("$$SOE") + len("$$SOE")
    eoe = raw_labeled.index("$$EOE")
    lines = [l for l in raw_labeled[soe:eoe].strip().splitlines() if l.strip()]
    for line in lines[:3]:
        print(f"  {line}")
    print(f"  ... ({len(lines)} total lines in probe window)")

    # --- Parsed output using the same raw fetch, labels off ---
    print("\n--- PARSED ---")
    raw = fetch_raw_probe(cfg["command"], cfg["ephem_type"], vec_labels="NO")
    if not raw:
        return

    if cfg["ephem_type"] == "VECTORS":
        df = parse_vectors(raw)
    else:
        df = parse_elements(raw)

    print(df.to_string(index=False))

    print("\n--- DTYPES ---")
    print(df.dtypes.to_string())

    print("\n--- SENTINEL CHECK ---")
    check_sentinels(df)


def main() -> None:
    all_tables = [c["table"] for c in QUERY_CONFIGS]
    parser = argparse.ArgumentParser(description="Probe Horizons queries before full fetch.")
    parser.add_argument(
        "table",
        nargs="?",
        choices=all_tables,
        default=None,
        help="Probe a single table. Omit to probe all four.",
    )
    args = parser.parse_args()

    targets = (
        [c for c in QUERY_CONFIGS if c["table"] == args.table]
        if args.table
        else QUERY_CONFIGS
    )

    for cfg in targets:
        probe(cfg)

    print("\n" + "=" * 60)
    print("Probe complete.")


if __name__ == "__main__":
    main()