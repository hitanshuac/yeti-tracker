from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import duckdb
import os
import sys
import pyarrow.parquet as pq

# Ensure the root directory is in the python path to support running `python src/main.py` directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.gold.reporting import get_category_footprint

app = FastAPI(title="Yeti-Tracker API")

DB_PATH = "data/yeti.duckdb"
DLQ_PATH = "data/quarantine_transactions.parquet"

@app.get("/api/dashboard-metrics")
def get_metrics():
    # 1. Total Emissions
    categories = get_category_footprint()
    total_emissions = sum(c["total_carbon_kg"] for c in categories)
    # Convert to tonnes for display if > 1000
    if total_emissions > 1000:
        display_emissions = f"{total_emissions/1000:.1f}k"
        unit = "tCO2e"
    else:
        display_emissions = f"{total_emissions:.1f}"
        unit = "kgCO2e"
    
    # 2. Active Scopes (Mocked as 3 for now based on UI)
    active_scopes = 3
    
    # 3. Quarantine Items
    quarantine_count = 0
    if os.path.exists(DLQ_PATH):
        try:
            table = pq.read_table(DLQ_PATH)
            quarantine_count = table.num_rows
        except Exception:
            pass
            
    # 4. Data Health
    valid_count = 0
    if os.path.exists(DB_PATH):
        try:
            conn = duckdb.connect(DB_PATH)
            valid_count = conn.execute("SELECT COUNT(*) FROM silver_transactions").fetchone()[0]
            conn.close()
        except Exception:
            pass
            
    total_records = valid_count + quarantine_count
    data_health = 100.0
    if total_records > 0:
        data_health = (valid_count / total_records) * 100
        
    return {
        "display_emissions": display_emissions,
        "emissions_unit": unit,
        "active_scopes": active_scopes,
        "quarantine_items": quarantine_count,
        "data_health": round(data_health, 1),
        "data_health_width": f"{round(data_health, 1)}%"
    }

@app.get("/api/category-footprint")
def get_categories():
    return get_category_footprint()

@app.get("/api/quarantine-data")
def get_quarantine_data():
    if not os.path.exists(DLQ_PATH):
        return []
    try:
        table = pq.read_table(DLQ_PATH)
        df = table.to_pandas()
        # Convert timestamp to string for JSON serialization
        if 'timestamp' in df.columns:
            df['timestamp'] = df['timestamp'].astype(str)
        return df.head(50).to_dict(orient="records")
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/ingestion-feed")
def get_ingestion_feed():
    passed_records = []
    try:
        conn = duckdb.connect(str(DB_PATH))
        query = "SELECT transaction_id, timestamp, mcc, amount_inr as amount, 'Passed' as status FROM silver_transactions ORDER BY timestamp DESC LIMIT 10"
        passed_df = conn.execute(query).df()
        passed_df['timestamp'] = passed_df['timestamp'].astype(str)
        passed_records = passed_df.to_dict(orient="records")
        conn.close()
    except Exception:
        pass

    failed_records = []
    try:
        if os.path.exists(DLQ_PATH):
            table = pq.read_table(DLQ_PATH)
            df = table.to_pandas()
            if 'timestamp' in df.columns:
                df['timestamp'] = df['timestamp'].astype(str)
            df['status'] = 'Quarantined'
            df = df.rename(columns={'amount_inr': 'amount'})
            cols = ['transaction_id', 'timestamp', 'mcc', 'amount', 'status']
            available_cols = [c for c in cols if c in df.columns]
            df = df[available_cols]
            failed_records = df.head(10).to_dict(orient="records")
    except Exception:
        pass

    combined = passed_records + failed_records
    combined.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return combined[:20]

@app.get("/")
def serve_dashboard():
    with open("src/frontend/components/dashboard.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.get("/ingestion")
def serve_ingestion():
    with open("src/frontend/components/ingestion.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

@app.get("/quarantine")
def serve_quarantine():
    with open("src/frontend/components/quarantine.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
