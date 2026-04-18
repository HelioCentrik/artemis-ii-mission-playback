# app/db.py
#
# In-memory DuckDB singleton. Loads all four artemis2 tables at startup,
# then releases the file lock immediately. All app queries go through get_con().

import duckdb

from app.config import (
    DB_PATH,
    TABLE_TRAJECTORY,
    TABLE_ELEMENTS,
    TABLE_MOON,
    TABLE_SUN,
)



_TABLES = (TABLE_TRAJECTORY, TABLE_ELEMENTS, TABLE_MOON, TABLE_SUN)

_CON: duckdb.DuckDBPyConnection | None = None


def get_con() -> duckdb.DuckDBPyConnection:
    """Return the in-memory DuckDB singleton, initializing it on first call."""
    global _CON
    if _CON is not None:
        return _CON

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run `python scripts/init_db.py` to build it."
        )

    _CON = duckdb.connect(":memory:")

    # Copy all tables from disk into memory, then release the file lock.
    _CON.execute(f"ATTACH '{DB_PATH}' AS src (READ_ONLY)")
    for table in _TABLES:
        _CON.execute(f"CREATE TABLE {table} AS SELECT * FROM src.{table}")
    _CON.execute("DETACH src")

    # Register derived metric views on the live connection.
    from app.sql import create_views
    create_views(_CON)

    return _CON