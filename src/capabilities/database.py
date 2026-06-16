"""
Module for database initialization and resilient data ingestion.
"""

import duckdb

from src.capabilities.observability import log_error


def init_duckdb(db_path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    """
    Initializes a DuckDB connection with optimized PRAGMA settings.

    Args:
        db_path: Path to the DuckDB file, or ':memory:'.

    Returns:
        The initialized DuckDB connection.
    """
    conn = duckdb.connect(db_path)
    # Configure WAL and Memory Limits per duckdb-optimizer skill
    if db_path != ":memory:":
        conn.execute("PRAGMA wal_autocheckpoint='1GB'")
    conn.execute("PRAGMA memory_limit='256MB'")

    # Create the target table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY,
            payload VARCHAR,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    return conn


def ingest_data_idempotent(conn: duckdb.DuckDBPyConnection, records: list[tuple[int, str]]) -> None:
    """
    Ingests records into DuckDB idempotently.
    Uses INSERT OR REPLACE to prevent duplicate rows on retry.

    Args:
        conn: The active DuckDB connection.
        records: A list of tuples containing (id, payload).
    """
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.executemany(
            """
            INSERT OR REPLACE INTO telemetry (id, payload)
            VALUES (?, ?)
        """,
            records,
        )
        conn.execute("COMMIT")
    except duckdb.Error as e:
        conn.execute("ROLLBACK")
        log_error(e, "src.capabilities.database.ingest_data_idempotent")
        raise
    except Exception as e:
        conn.execute("ROLLBACK")
        log_error(e, "src.capabilities.database.ingest_data_idempotent")
        raise
