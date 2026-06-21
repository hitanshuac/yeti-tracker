import pytest

from src.history import (
    _get_connection,
    append_history,
    fetch_historical_kpis,
    fetch_history_dataframe,
    seed_demo_history,
)


@pytest.fixture
def test_db_path(tmp_path):
    """Provide an isolated DuckDB file path for testing."""
    # pylint: disable=line-too-long,duplicate-code,missing-docstring,import-outside-toplevel,redefined-outer-name,no-else-raise,too-few-public-methods
    return str(tmp_path / "test_history.duckdb")


def test_append_history_valid(test_db_path):
    """Verify appending a valid confession creates a row."""
    session_id = "test-session-123"
    append_history(session_id, 1500.5, "Human", db_path=test_db_path)

    conn = _get_connection(test_db_path)
    rows = conn.execute("SELECT * FROM user_history WHERE session_id = ?", [session_id]).fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0][0] == session_id
    assert rows[0][2] == 1500.5
    assert rows[0][5] == "Human"


def test_append_history_invalid(test_db_path):
    """Verify guard clauses enforce defensive programming rules."""
    with pytest.raises(ValueError, match="session_id must be a non-empty string"):
        append_history("", 1500.5, "Human", db_path=test_db_path)

    with pytest.raises(ValueError, match="daily_carbon_kg must be >= 0"):
        append_history("valid-id", -50.0, "Human", db_path=test_db_path)


def test_seed_demo_history(test_db_path):
    """Verify the seeder injects exactly 31 rows (30 days ago to today inclusive)."""
    session_id = "demo-session"
    seed_demo_history(session_id, db_path=test_db_path)

    conn = _get_connection(test_db_path)
    count = conn.execute("SELECT COUNT(*) FROM user_history WHERE session_id = ?", [session_id]).fetchone()[0]
    conn.close()

    assert count == 31


def test_fetch_historical_kpis(test_db_path):
    """Verify KPI extraction handles both populated and empty histories."""
    session_id = "kpi-session"

    # Empty history
    kpi = fetch_historical_kpis(session_id, db_path=test_db_path)
    assert kpi == "This is the user's first confession."

    # Populated history
    append_history(session_id, 10.0, "Human", db_path=test_db_path)
    append_history(session_id, 20.0, "Human", db_path=test_db_path)

    kpi2 = fetch_historical_kpis(session_id, db_path=test_db_path)
    assert "confessed 2 times" in kpi2
    assert "15.0 kg" in kpi2


def test_fetch_history_dataframe(test_db_path):
    """Verify history returns a valid Pandas DataFrame."""
    session_id = "df-session"
    append_history(session_id, 5.0, "Human", db_path=test_db_path)

    df = fetch_history_dataframe(session_id, db_path=test_db_path)
    assert df is not None
    assert len(df) == 1
    assert list(df.columns) == ["timestamp", "daily_carbon_kg"]
    assert df.iloc[0]["daily_carbon_kg"] == 5.0

    # Verify outlier filtering (> 1000 daily kg)
    append_history(session_id, 1500.0, "Cat 3", db_path=test_db_path)
    df_filtered = fetch_history_dataframe(session_id, db_path=test_db_path)
    assert len(df_filtered) == 1  # The 1500 value should be excluded


def test_legacy_schema_migration(tmp_path):
    """Simulate 'Schema Drift' by creating a legacy 4-column db and verifying the hook upgrades it."""
    import duckdb

    legacy_db = str(tmp_path / "v1_yeti.duckdb")

    # 1. Create a legacy v1 database (4 columns)
    conn = duckdb.connect(legacy_db)
    conn.execute("""
        CREATE TABLE user_history (
            session_id VARCHAR,
            timestamp TIMESTAMP,
            daily_carbon_kg DOUBLE,
            tier VARCHAR
        )
    """)
    conn.execute("INSERT INTO user_history VALUES ('legacy-user', current_timestamp, 10.0, 'Human')")
    conn.close()

    # 2. Trigger the startup hook
    conn2 = _get_connection(legacy_db)

    # 3. Verify columns exist and legacy data is preserved
    columns = [row[1] for row in conn2.execute("PRAGMA table_info('user_history')").fetchall()]
    assert "bus_km" in columns
    assert "train_metro_km" in columns

    data = conn2.execute("SELECT bus_km, train_metro_km FROM user_history").fetchone()
    assert data[0] == 0.0
    assert data[1] == 0.0

    # 4. Verify we can insert new 6-column data without BinderException
    append_history("new-user", 5.0, "Yeti", db_path=legacy_db)
    new_data = conn2.execute("SELECT bus_km, train_metro_km FROM user_history WHERE session_id='new-user'").fetchone()
    assert new_data[0] == 0.0
    assert new_data[1] == 0.0

    conn2.close()
