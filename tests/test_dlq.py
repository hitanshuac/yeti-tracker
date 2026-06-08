import pytest
import os
import pyarrow.parquet as pq
from src.ingestion.processor import process_raw_activities

TEST_DB_PATH = "data/test_dlq_yeti.duckdb"
TEST_DLQ_PATH = "data/test_quarantine.parquet"

@pytest.fixture(autouse=True)
def setup_teardown():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    if os.path.exists(TEST_DLQ_PATH):
        os.remove(TEST_DLQ_PATH)
    yield
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    if os.path.exists(TEST_DLQ_PATH):
        os.remove(TEST_DLQ_PATH)

def test_dlq_routing():
    raw_activities = [
        {
            "activity_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "user_1",
            "activity_type": "transport",
            "carbon_kg": 15.0,
            "timestamp": "2023-10-10T12:00:00"
        },
        {
            "activity_id": "123e4567-e89b-12d3-a456-426614174001",
            "user_id": "user_1",
            "activity_type": "electricity",
            "carbon_kg": -5.0, # INVALID: negative carbon
            "timestamp": "2023-10-10T13:00:00"
        },
        {
            "activity_id": "not-a-uuid", # INVALID: bad uuid
            "user_id": "user_2",
            "activity_type": "food",
            "carbon_kg": 10.0,
            "timestamp": "2023-10-10T14:00:00"
        }
    ]
    
    process_raw_activities(raw_activities, TEST_DB_PATH, TEST_DLQ_PATH)
    
    # Check DLQ exists
    assert os.path.exists(TEST_DLQ_PATH)
    table = pq.read_table(TEST_DLQ_PATH)
    assert table.num_rows == 2
    
    # Check DuckDB has the valid one
    import duckdb
    conn = duckdb.connect(TEST_DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM activities").fetchone()[0]
    assert count == 1
    conn.close()
