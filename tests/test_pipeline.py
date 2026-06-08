import pytest
import os
import json
import uuid
import duckdb
import pyarrow.parquet as pq
from datetime import datetime

from src.silver.enrichment import process_bronze_to_silver
from src.gold.reporting import get_user_footprint, get_category_footprint

# Overwrite paths for testing
import src.silver.enrichment as enrichment
import src.gold.reporting as reporting

TEST_RAW_DIR = "data/test_raw_transactions"
TEST_DB_PATH = "data/test_yeti.duckdb"
TEST_DLQ_PATH = "data/test_quarantine_transactions.parquet"

enrichment.RAW_DIR = TEST_RAW_DIR
enrichment.DB_PATH = TEST_DB_PATH
enrichment.DLQ_PATH = TEST_DLQ_PATH
reporting.DB_PATH = TEST_DB_PATH

@pytest.fixture(autouse=True)
def setup_teardown():
    os.makedirs(TEST_RAW_DIR, exist_ok=True)
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    if os.path.exists(TEST_DLQ_PATH):
        os.remove(TEST_DLQ_PATH)
    
    yield
    
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    if os.path.exists(TEST_DLQ_PATH):
        os.remove(TEST_DLQ_PATH)
    for f in os.listdir(TEST_RAW_DIR):
        os.remove(os.path.join(TEST_RAW_DIR, f))
    os.rmdir(TEST_RAW_DIR)

def test_full_pipeline():
    # 1. Generate Mock Bronze Data
    valid_tx = {
        "transaction_id": str(uuid.uuid4()),
        "user_id": "test_user",
        "mcc": "4111", # Transport (0.05 factor)
        "amount_inr": 100.0,
        "timestamp": datetime.now().isoformat()
    }
    
    invalid_tx = {
        "transaction_id": "not-a-uuid", # INVALID
        "user_id": "test_user",
        "mcc": "5411",
        "amount_inr": -10.0, # INVALID
        "timestamp": datetime.now().isoformat()
    }
    
    with open(os.path.join(TEST_RAW_DIR, "batch_1.json"), "w") as f:
        json.dump([valid_tx, invalid_tx], f)

    # 2. Run Silver Layer
    process_bronze_to_silver()
    
    # 3. Verify Silver DuckDB (Valid Record)
    conn = duckdb.connect(TEST_DB_PATH)
    res = conn.execute("SELECT carbon_kg, category FROM silver_transactions WHERE user_id='test_user'").fetchone()
    assert res is not None
    assert res[0] == 5.0 # 100.0 * 0.05
    assert res[1] == "Local Commuter Transport"
    conn.close()
    
    # 4. Verify Parquet DLQ (Invalid Record)
    assert os.path.exists(TEST_DLQ_PATH)
    table = pq.read_table(TEST_DLQ_PATH)
    assert table.num_rows == 1
    
    # 5. Verify Gold Layer
    user_report = get_user_footprint("test_user")
    assert user_report["total_carbon_kg"] == 5.0
    assert user_report["total_transactions"] == 1
    
    cat_report = get_category_footprint()
    assert len(cat_report) == 1
    assert cat_report[0]["category"] == "Local Commuter Transport"
    assert cat_report[0]["total_carbon_kg"] == 5.0
