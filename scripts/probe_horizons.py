# scripts/probe_horizons.py

import sys
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import HORIZONS_URL, SPACECRAFT_ID, CENTER, REF_SYSTEM, REF_PLANE, OUT_UNITS

BASE_PARAMS = {
    "format":     "json",
    "COMMAND":    f"'{SPACECRAFT_ID}'",
    "OBJ_DATA":   "NO",
    "MAKE_EPHEM": "YES",
    "EPHEM_TYPE": "VECTORS",
    "CENTER":     f"'{CENTER}'",
    "START_TIME": "'2026-Apr-02 02:00'",
    "STOP_TIME":  "'2026-Apr-02 02:05'",   # tiny window - just 5 rows
    "STEP_SIZE":  "'1m'",
    "VEC_LABELS": "YES",                   # keep labels so we can see column names
    "OUT_UNITS":  OUT_UNITS,
    "CSV_FORMAT": "YES",
    "REF_PLANE":  REF_PLANE,
    "REF_SYSTEM": REF_SYSTEM,
}

for vec_table in ["1", "2", "3", "4", "6"]:
    print(f"\n{'='*60}")
    print(f"VEC_TABLE = {vec_table}")
    print('='*60)

    params = {**BASE_PARAMS, "VEC_TABLE": vec_table}
    resp = requests.get(HORIZONS_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        print(f"  ERROR: {data['error']}")
        continue

    result = data.get("result", "")

    if "$$SOE" not in result:
        print("  No data block returned")
        # print first 500 chars of result to see what we got
        print(result[:500])
        continue

    soe = result.index("$$SOE") + len("$$SOE")
    eoe = result.index("$$EOE")
    block = result[soe:eoe].strip()

    lines = [l for l in block.splitlines() if l.strip()]
    print(f"  Rows in block: {len(lines)}")
    print(f"  First row:\n    {lines[0]}")
    if len(lines) > 1:
        print(f"  Second row:\n    {lines[1]}")