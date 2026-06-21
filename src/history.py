"""
# pylint: disable=line-too-long,duplicate-code,missing-docstring,import-outside-toplevel,redefined-outer-name,no-else-raise,too-few-public-methods
History persistence layer using DuckDB.

Manages the user_history table: init, append, query, and demo seeding.
Uses a module-level connection getter for connection reuse.
"""

import datetime
import json
import os
import random

import duckdb
import pandas as pd

# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

_DB_PATH = "data/yeti.duckdb"


def _get_connection(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection and ensure the history table exists and is up-to-date.

    Args:
        db_path: Override path for testing. Defaults to ``data/yeti.duckdb``.

    Returns:
        An initialized DuckDB connection.
    """
    path = db_path or _DB_PATH
    conn = duckdb.connect(path)

    # Check if table exists
    tables = conn.execute(
        "SELECT * FROM information_schema.tables WHERE table_name='user_history'"
    ).fetchall()

    if not tables:
        # Initial schema creation
        conn.execute("""
            CREATE TABLE user_history (
                session_id VARCHAR,
                timestamp TIMESTAMP,
                daily_carbon_kg DOUBLE,
                bus_km DOUBLE,
                train_metro_km DOUBLE,
                tier VARCHAR
            )
        """)
    else:
        _run_migrations(conn)

    return conn


def _run_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    """Startup Migration Hook: check for missing columns (Schema Drift)."""
    columns = [
        row[1] for row in conn.execute("PRAGMA table_info('user_history')").fetchall()
    ]
    if "bus_km" not in columns:
        conn.execute("ALTER TABLE user_history ADD COLUMN bus_km DOUBLE DEFAULT 0.0")
    if "train_metro_km" not in columns:
        conn.execute(
            "ALTER TABLE user_history ADD COLUMN train_metro_km DOUBLE DEFAULT 0.0"
        )


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------


def append_history(
    session_id: str,
    daily_carbon_kg: float,
    tier: str,
    db_path: str | None = None,
) -> None:
    """Persist a single confession event.

    Args:
        session_id: UUID identifying the user session.
        daily_carbon_kg: The daily carbon output in kg.
        tier: The gamification tier string.
        db_path: Override path for testing.
    """
    if not session_id or not isinstance(session_id, str):
        raise ValueError(f"session_id must be a non-empty string, got: {session_id!r}")
    if daily_carbon_kg < 0:
        raise ValueError(f"daily_carbon_kg must be >= 0, got: {daily_carbon_kg!r}")

    conn = _get_connection(db_path)
    conn.execute(
        "INSERT INTO user_history (session_id, timestamp, daily_carbon_kg, bus_km, train_metro_km, tier) VALUES (?, ?, ?, ?, ?, ?)",
        [session_id, datetime.datetime.now(), daily_carbon_kg, 0.0, 0.0, tier],
    )
    conn.close()


def seed_demo_history(session_id: str, db_path: str | None = None) -> None:
    """Seed 30 days of random history for demo purposes.

    Args:
        session_id: UUID for the session to seed.
        db_path: Override path for testing.
    """
    conn = _get_connection(db_path)
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)
    curr = start_date
    base = 3.28  # ~1200 kg/year

    while curr <= end_date:
        d_val = base + random.uniform(-0.5, 2.0)
        d_val = max(0.0, d_val)  # Prevent negative daily footprints
        conn.execute(
            "INSERT INTO user_history (session_id, timestamp, daily_carbon_kg, bus_km, train_metro_km, tier) VALUES (?, ?, ?, ?, ?, ?)",
            [session_id, curr, d_val, 0.0, 0.0, "Human"],
        )
        curr += datetime.timedelta(days=1)

    conn.close()


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------


def fetch_historical_kpis(session_id: str, db_path: str | None = None) -> str:
    """Extract aggregate KPIs for Silent Accountability.

    Args:
        session_id: UUID identifying the user session.
        db_path: Override path for testing.

    Returns:
        A human-readable KPI summary string.
    """
    conn = _get_connection(db_path)
    res = conn.execute(
        "SELECT COUNT(*), AVG(daily_carbon_kg) FROM user_history WHERE session_id = ?",
        [session_id],
    ).fetchone()
    conn.close()

    if res and res[0] > 0:
        return f"User has confessed {res[0]} times. Their average daily footprint is {res[1]:.1f} kg."
    return "This is the user's first confession."


def fetch_history_dataframe(
    session_id: str, db_path: str | None = None
) -> pd.DataFrame:
    """Fetch the full history for charting.

    Args:
        session_id: UUID identifying the user session.
        db_path: Override path for testing.

    Returns:
        DataFrame with columns ``timestamp`` and ``daily_carbon_kg``.
    """
    conn = _get_connection(db_path)
    query = (
        "SELECT timestamp, daily_carbon_kg FROM user_history "
        "WHERE session_id = ? AND daily_carbon_kg < 1000 "
        "ORDER BY timestamp ASC"
    )
    df = conn.execute(query, [session_id]).fetchdf()
    conn.close()
    return df


# ---------------------------------------------------------------------------
# Internal error logging
# ---------------------------------------------------------------------------


def _log_history_error(error: Exception) -> None:
    """Minimal error logger for history operations."""
    log_file = "data/error_logs.json"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    try:
        with open(log_file, encoding="utf-8") as f:
            logs = json.load(f)
            if not isinstance(logs, list):
                logs = []
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []

    logs.append(
        {
            "error_type": type(error).__name__,
            "component": "history",
            "message": str(error),
            "status": "UNRESOLVED",
            "resolution_strategy": None,
        }
    )

    temp_file = f"{log_file}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    os.replace(temp_file, log_file)
