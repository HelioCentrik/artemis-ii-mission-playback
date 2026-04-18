# scripts/probe_db.py

import sys
from pathlib import Path
import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import (
    DB_PATH,
    TABLE_TRAJECTORY,
    TABLE_ELEMENTS,
    TABLE_MOON,
    TABLE_SUN,
)

NUMERIC_COLS = {
    TABLE_TRAJECTORY: ["x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms",
                       "lt_sec", "rg_km", "rr_kms"],
    TABLE_ELEMENTS:   ["ec", "qr_km", "inc_deg", "om_deg", "w_deg",
                       "ta_deg", "a_km", "ad_km", "pr_d"],
    TABLE_MOON:       ["x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms",
                       "lt_sec", "rg_km", "rr_kms"],
    TABLE_SUN:        ["x_km", "y_km", "z_km", "vx_kms", "vy_kms", "vz_kms",
                       "lt_sec", "rg_km", "rr_kms"],
}

EXPECTED_ROWS = 12_836
SECTION = "=" * 60


def probe_table(con: duckdb.DuckDBPyConnection, table: str) -> None:
    print(f"\n{SECTION}")
    print(f"  TABLE: {table}")
    print(SECTION)

    # --- Row count ---
    row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    status = "✓" if row_count == EXPECTED_ROWS else f"⚠ EXPECTED {EXPECTED_ROWS}"
    print(f"\nROW COUNT: {row_count:,}  {status}")

    # --- Date range ---
    date_range = con.execute(f"""
        SELECT
            MIN(datetime_utc) AS first_row,
            MAX(datetime_utc) AS last_row
        FROM {table}
    """).df()
    print(f"\nDATE RANGE:")
    print(f"  First: {date_range['first_row'].iloc[0]}")
    print(f"  Last:  {date_range['last_row'].iloc[0]}")

    # --- Dtypes ---
    schema = con.execute(f"DESCRIBE {table}").df()
    print(f"\nSCHEMA:")
    print(schema[["column_name", "column_type"]].to_string(index=False))

    # --- Null check on numeric columns ---
    cols = NUMERIC_COLS.get(table, [])
    if cols:
        null_exprs = ", ".join(
            f"COUNT(*) - COUNT({c}) AS {c}_nulls" for c in cols
        )
        nulls = con.execute(f"SELECT {null_exprs} FROM {table}").df()

        # ad_km and pr_d nulls in orion_elements are expected — flag separately
        expected_null_cols = {"ad_km", "pr_d"} if table == TABLE_ELEMENTS else set()

        unexpected_nulls = {
            col.replace("_nulls", ""): int(nulls[col].iloc[0])
            for col in nulls.columns
            if int(nulls[col].iloc[0]) > 0
            and col.replace("_nulls", "") not in expected_null_cols
        }
        expected_nulls_found = {
            col.replace("_nulls", ""): int(nulls[col].iloc[0])
            for col in nulls.columns
            if int(nulls[col].iloc[0]) > 0
            and col.replace("_nulls", "") in expected_null_cols
        }

        if unexpected_nulls:
            print(f"\nNULLS — ⚠ UNEXPECTED:")
            for col, n in unexpected_nulls.items():
                print(f"  {col}: {n}")
        else:
            print(f"\nNULLS (non-hyperbolic cols): ✓ none")

        if expected_nulls_found:
            print(f"NULLS — expected (hyperbolic phase):")
            for col, n in expected_nulls_found.items():
                print(f"  {col}: {n}  ✓")

    # --- orion_elements specific: eccentricity breakdown ---
    if table == TABLE_ELEMENTS:
        ec_stats = con.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE ec < 1)  AS bound_rows,
                COUNT(*) FILTER (WHERE ec >= 1) AS hyperbolic_rows,
                MIN(ec)  AS ec_min,
                MAX(ec)  AS ec_max
            FROM {table}
        """).fetchone()
        print(f"\nECCENTRICITY BREAKDOWN:")
        print(f"  Bound (ec < 1):      {ec_stats[0]:,}")
        print(f"  Hyperbolic (ec >= 1): {ec_stats[1]:,}")
        print(f"  Range: {ec_stats[2]:.6f} → {ec_stats[3]:.6f}")

    # --- orion_trajectory specific: speed and range sanity ---
    if table == TABLE_TRAJECTORY:
        sanity = con.execute(f"""
            SELECT
                MIN(rg_km)  AS min_range_km,
                MAX(rg_km)  AS max_range_km,
                MIN(SQRT(vx_kms*vx_kms + vy_kms*vy_kms + vz_kms*vz_kms)) AS min_speed_kms,
                MAX(SQRT(vx_kms*vx_kms + vy_kms*vy_kms + vz_kms*vz_kms)) AS max_speed_kms
            FROM {table}
        """).fetchone()
        print(f"\nSANITY — RANGE & SPEED:")
        print(f"  Range:  {sanity[0]:,.0f} km  →  {sanity[1]:,.0f} km")
        print(f"  Speed:  {sanity[2]:.3f} km/s  →  {sanity[3]:.3f} km/s")

    # --- Sample rows ---
    sample = con.execute(f"""
        SELECT * FROM {table} LIMIT 3
    """).df()
    print(f"\nSAMPLE (first 3 rows):")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 120)
    print(sample.to_string(index=False))


def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Run:  python scripts/init_db.py")
        sys.exit(1)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    tables = [TABLE_TRAJECTORY, TABLE_ELEMENTS, TABLE_MOON, TABLE_SUN]
    for table in tables:
        # Check if table exists before probing
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table]
        ).fetchone()[0]
        if exists:
            probe_table(con, table)
        else:
            print(f"\n⚠  Table '{table}' not found — skipped")

    con.close()
    print(f"\n{SECTION}")
    print("  PROBE COMPLETE")
    print(SECTION)


if __name__ == "__main__":
    main()