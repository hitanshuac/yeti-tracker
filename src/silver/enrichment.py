import os
import json
import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from typing import Dict, Any
from pydantic import ValidationError
from datetime import datetime

from src.models.carbon_activity import RawTransaction

RAW_DIR = "data/raw_transactions"
DB_PATH = "data/yeti.duckdb"
DLQ_PATH = "data/quarantine_transactions.parquet"
FACTORS_PATH = "src/data/emission_factors.json"

def init_db():
    conn = duckdb.connect(DB_PATH)
    conn.execute("PRAGMA memory_limit='2GB'")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS silver_transactions (
            transaction_id UUID PRIMARY KEY,
            user_id VARCHAR,
            mcc VARCHAR,
            category VARCHAR,
            amount_inr DOUBLE,
            carbon_kg DOUBLE,
            timestamp TIMESTAMP
        )
    """)
    conn.close()

def load_factors() -> Dict[str, Any]:
    with open(FACTORS_PATH, "r") as f:
        return json.load(f)["factors"]

def process_bronze_to_silver():
    """Reads raw JSONs, validates via Pydantic, routes to DLQ or enriches to DuckDB."""
    init_db()
    factors = load_factors()
    
    if not os.path.exists(RAW_DIR):
        return

    json_files = [f for f in os.listdir(RAW_DIR) if f.endswith(".json")]
    if not json_files:
        print("No raw transactions to process.")
        return

    valid_records = []
    invalid_records = []

    # Process all files
    for filename in json_files:
        filepath = os.path.join(RAW_DIR, filename)
        with open(filepath, "r") as f:
            try:
                batch = json.load(f)
                for record in batch:
                    try:
                        # Validate
                        tx = RawTransaction(**record)
                        
                        # Enrich
                        mcc_data = factors.get(tx.mcc, {"category": "Unknown", "kg_co2_per_inr": 0.0})
                        carbon_kg = tx.amount_inr * mcc_data["kg_co2_per_inr"]
                        
                        enriched_record = {
                            "transaction_id": str(tx.transaction_id),
                            "user_id": tx.user_id,
                            "mcc": tx.mcc,
                            "category": mcc_data["category"],
                            "amount_inr": tx.amount_inr,
                            "carbon_kg": round(carbon_kg, 4),
                            "timestamp": tx.timestamp.isoformat()
                        }
                        valid_records.append(enriched_record)
                    except ValidationError as e:
                        # DLQ Routing
                        invalid_records.append({
                            "raw_record": json.dumps(record),
                            "error_message": str(e),
                            "timestamp": datetime.now().isoformat()
                        })
            except json.JSONDecodeError:
                print(f"Failed to parse {filename}")

        # Delete file after processing to save space
        os.remove(filepath)

    # Dump invalid records to Parquet DLQ
    if invalid_records:
        table = pa.Table.from_pylist(invalid_records)
        if os.path.exists(DLQ_PATH):
            existing_table = pq.read_table(DLQ_PATH)
            table = pa.concat_tables([existing_table, table])
        pq.write_table(table, DLQ_PATH)
        print(f"Quarantined {len(invalid_records)} invalid records to DLQ.")

    # Idempotent write to DuckDB
    if valid_records:
        arrow_table = pa.Table.from_pylist(valid_records)
        conn = duckdb.connect(DB_PATH)
        conn.execute("PRAGMA memory_limit='2GB'")
        conn.register("arrow_table", arrow_table)
        
        conn.execute("""
            INSERT OR REPLACE INTO silver_transactions 
            SELECT 
                CAST(transaction_id AS UUID), 
                user_id, 
                mcc,
                category,
                amount_inr, 
                carbon_kg, 
                CAST(timestamp AS TIMESTAMP)
            FROM arrow_table
        """)
        conn.close()
        print(f"Successfully enriched and loaded {len(valid_records)} transactions to Silver layer.")

if __name__ == "__main__":
    process_bronze_to_silver()
