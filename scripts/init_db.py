# scripts/init_db.py
#
# Initializes the Artemis II DuckDB database.
# Loops through all four Horizons query configs, checks each table for existence
# and expected row count, skips if already populated, fetches and writes if not.
#
# Usage:
#   python scripts/init_db.py            # skip tables that already have full data
#   python scripts/init_db.py --force    # re-fetch and overwrite everything

import sys
import argparse
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import DATA_DIR, DB_PATH, EXPECTED_ROW_COUNT
from scripts.fetch_horizons import QUERY_CONFIGS, fetch



def table_row_count(con: duckdb.DuckDBPyConnection, table: str) -> int:
    """Returns row count for table, or 0 if table doesn't exist."""
    exists = con.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = ?
    """, [table]).fetchone()[0]

    if not exists:
        return 0

    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def write_table(con: duckdb.DuckDBPyConnection, table: str, df) -> None:
    con.execute(f"DROP TABLE IF EXISTS {table}")
    con.execute(f"CREATE TABLE {table} AS SELECT * FROM df")
    row_count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"    Written — {row_count:,} rows")


def init_db(force: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))

    print(f"Database: {DB_PATH}")
    print(f"Expected rows per table: {EXPECTED_ROW_COUNT:,}")
    print(f"Force re-fetch: {force}")
    print("=" * 52)

    for cfg in QUERY_CONFIGS:
        table = cfg["table"]
        label = cfg["label"]

        print(f"\n[{label}]  →  {table}")

        current_rows = table_row_count(con, table)

        if not force and current_rows >= EXPECTED_ROW_COUNT:
            print(f"    Skipping — {current_rows:,} rows already present")
            continue

        if current_rows > 0:
            print(f"    Found {current_rows:,} rows (below threshold or --force set) — re-fetching")
        else:
            print(f"    Table empty or missing — fetching from Horizons")

        df = fetch(cfg)
        write_table(con, table, df)

    print("\n" + "=" * 52)
    print("Final state:")
    for cfg in QUERY_CONFIGS:
        rows = table_row_count(con, cfg["table"])
        status = "✓" if rows >= EXPECTED_ROW_COUNT else "✗ INCOMPLETE"
        print(f"  {status}  {cfg['table']:<22}  {rows:>7,} rows")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize Artemis II DuckDB database.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch all tables even if they already have data",
    )
    args = parser.parse_args()
    init_db(force=args.force)