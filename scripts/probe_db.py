# scripts/probe_db.py

import sys
from pathlib import Path
import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import DB_PATH, TABLE_TRAJECTORY

con = duckdb.connect(str(DB_PATH))

print("=== SCHEMA ===")
print(con.execute(f"DESCRIBE {TABLE_TRAJECTORY}").df().to_string(index=False))

print("\n=== ROW COUNT ===")
print(con.execute(f"SELECT COUNT(*) AS rows FROM {TABLE_TRAJECTORY}").fetchone()[0])

print("\n=== DATE RANGE ===")
print(con.execute(f"""
    SELECT 
        MIN(datetime_utc) AS first_row,
        MAX(datetime_utc) AS last_row
    FROM {TABLE_TRAJECTORY}
""").df().to_string(index=False))

print("\n=== NULLS ===")
print(con.execute(f"""
    SELECT
        COUNT(*) - COUNT(x_km)    AS x_nulls,
        COUNT(*) - COUNT(y_km)    AS y_nulls,
        COUNT(*) - COUNT(z_km)    AS z_nulls,
        COUNT(*) - COUNT(vx_kms)  AS vx_nulls,
        COUNT(*) - COUNT(vy_kms)  AS vy_nulls,
        COUNT(*) - COUNT(vz_kms)  AS vz_nulls,
        COUNT(*) - COUNT(lt_sec)  AS lt_nulls,
        COUNT(*) - COUNT(rg_km)   AS rg_nulls,
        COUNT(*) - COUNT(rr_kms)  AS rr_nulls
    FROM {TABLE_TRAJECTORY}
""").df().to_string(index=False))

print("\n=== SAMPLE (first 3 rows) ===")
print(con.execute(f"SELECT * FROM {TABLE_TRAJECTORY} LIMIT 3").df().to_string(index=False))

print("\n=== SAMPLE (last 3 rows) ===")
print(con.execute(f"""
    SELECT * FROM {TABLE_TRAJECTORY} 
    ORDER BY datetime_utc DESC LIMIT 3
""").df().to_string(index=False))

con.close()