import pyarrow as pa
import pyarrow.parquet as pq
from typing import List, Dict, Any
from pydantic import ValidationError
import os
import json
from datetime import datetime

from src.models.carbon_activity import CarbonActivity
from src.ingestion.duckdb_ingest import ingest_activities, init_db

def process_raw_activities(raw_data: List[Dict[str, Any]], db_path: str = "data/yeti.duckdb", dlq_path: str = "data/quarantine_activities.parquet"):
    if not os.path.exists(db_path):
        init_db(db_path)
        
    valid_activities = []
    invalid_records = []
    
    for record in raw_data:
        try:
            activity = CarbonActivity(**record)
            valid_activities.append(activity)
        except ValidationError as e:
            # Add to DLQ
            invalid_records.append({
                "raw_record": json.dumps(record),
                "error_message": str(e),
                "timestamp": datetime.now().isoformat()
            })
            
    # Process valid records
    if valid_activities:
        ingest_activities(valid_activities, db_path)
        
    # Dump invalid records to Parquet
    if invalid_records:
        table = pa.Table.from_pylist(invalid_records)
        
        # Append to existing parquet if it exists
        if os.path.exists(dlq_path):
            existing_table = pq.read_table(dlq_path)
            # Schema must match. Since it's string columns, it's safe.
            table = pa.concat_tables([existing_table, table])
            
        pq.write_table(table, dlq_path)
