import pytest
import duckdb
from datetime import datetime
import os
import uuid

from src.models.carbon_activity import CarbonActivity
from src.ingestion.duckdb_ingest import ingest_activities, init_db

TEST_DB_PATH = "data/test_yeti.duckdb"

@pytest.fixture(autouse=True)
def setup_teardown():
    # Teardown before
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    init_db(TEST_DB_PATH)
    yield
    # Teardown after
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

def test_ingest_activities():
    activities = [
        CarbonActivity(
            activity_id=uuid.uuid4(),
            user_id="user_1",
            activity_type="transport",
            carbon_kg=5.0,
            timestamp=datetime.now()
        ),
        CarbonActivity(
            activity_id=uuid.uuid4(),
            user_id="user_1",
            activity_type="electricity",
            carbon_kg=2.0,
            timestamp=datetime.now()
        )
    ]
    
    ingest_activities(activities, TEST_DB_PATH)
    
    conn = duckdb.connect(TEST_DB_PATH)
    res = conn.execute("SELECT COUNT(*) FROM activities").fetchone()
    assert res[0] == 2
    
    # Test Idempotency
    ingest_activities(activities, TEST_DB_PATH)
    res = conn.execute("SELECT COUNT(*) FROM activities").fetchone()
    assert res[0] == 2 # Count should still be 2 because of INSERT OR REPLACE
    conn.close()
