# scripts/init_db.py

import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR, DB_PATH, TABLE_TRAJECTORY
from scripts.fetch_horizons import fetch_trajectory


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = fetch_trajectory()

    print(f"\nWriting to DuckDB: {DB_PATH}")
    con = duckdb.connect(str(DB_PATH))

    con.execute(f"DROP TABLE IF EXISTS {TABLE_TRAJECTORY}")
    con.execute(
        f"CREATE TABLE {TABLE_TRAJECTORY} AS SELECT * FROM df"
    )

    row_count = con.execute(
        f"SELECT COUNT(*) FROM {TABLE_TRAJECTORY}"
    ).fetchone()[0]

    print(f"  Table '{TABLE_TRAJECTORY}' written — {row_count:,} rows")

    # Quick sanity check
    sample = con.execute(
        f"SELECT datetime_utc, x_km, y_km, z_km FROM {TABLE_TRAJECTORY} LIMIT 3"
    ).df()
    print("\n--- Sanity check ---")
    print(sample.to_string(index=False))

    con.close()
    print("\nDone. Database ready.")


if __name__ == "__main__":
    init_db()