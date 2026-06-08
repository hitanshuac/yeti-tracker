import duckdb
import pyarrow as pa
from typing import List
from src.models.carbon_activity import CarbonActivity

def init_db(db_path: str = "data/yeti.duckdb"):
    # DuckDB Optimizer Skill: memory limits and WAL
    conn = duckdb.connect(db_path)
    conn.execute("PRAGMA memory_limit='2GB'")
    # Note: duckdb WAL is automatic on disk, but we can set pragmas if needed
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            activity_id UUID PRIMARY KEY,
            user_id VARCHAR,
            activity_type VARCHAR,
            carbon_kg DOUBLE,
            timestamp TIMESTAMP
        )
    """)
    conn.close()

def ingest_activities(activities: List[CarbonActivity], db_path: str = "data/yeti.duckdb"):
    if not activities:
        return

    # Convert Pydantic models to dicts
    data = [act.model_dump() for act in activities]
    
    # Convert to PyArrow Table for efficient memory transfer
    # PyArrow handles UUID to string/bytes if necessary, but DuckDB handles UUID natively.
    # To be safe with pyarrow, we can convert UUID to string first, or use pyarrow's native support.
    # Pydantic's model_dump uses UUID objects. PyArrow supports UUID.
    # Let's convert them to strings to avoid type matching issues between pyarrow and duckdb UUID.
    
    for d in data:
        d['activity_id'] = str(d['activity_id'])

    arrow_table = pa.Table.from_pylist(data)

    conn = duckdb.connect(db_path)
    conn.execute("PRAGMA memory_limit='2GB'")
    
    # Register the pyarrow table
    conn.register("arrow_table", arrow_table)
    
    # Idempotent insert
    conn.execute("""
        INSERT OR REPLACE INTO activities 
        SELECT 
            CAST(activity_id AS UUID), 
            user_id, 
            activity_type, 
            carbon_kg, 
            timestamp 
        FROM arrow_table
    """)
    
    conn.close()
