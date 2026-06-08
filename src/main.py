from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import duckdb
import os
import sys

# Ensure the root directory is in the python path to support running `python src/main.py` directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = FastAPI(title="Yeti-Tracker API")

# Security: CORS and strict security headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

DB_PATH = "data/yeti.duckdb"

@app.get("/api/stats/diet")
def get_diet_stats():
    try:
        conn = duckdb.connect()
        conn.execute("PRAGMA memory_limit='1GB'; PRAGMA threads=2;")
        query = """
            SELECT food_type, AVG(carbon_footprint_kg) as avg_co2 
            FROM read_csv_auto('data/personal_carbon_footprint_sample.csv') 
            GROUP BY food_type 
            ORDER BY avg_co2 DESC
        """
        df = conn.execute(query).df()
        return df.to_dict(orient="records")
    except Exception:
        return []

@app.get("/api/stats/transport")
def get_transport_stats():
    try:
        conn = duckdb.connect()
        conn.execute("PRAGMA memory_limit='1GB'; PRAGMA threads=2;")
        query = """
            SELECT transport_mode, AVG(carbon_footprint_kg) as avg_co2 
            FROM read_csv_auto('data/personal_carbon_footprint_sample.csv') 
            GROUP BY transport_mode 
            ORDER BY avg_co2 DESC
        """
        df = conn.execute(query).df()
        return df.to_dict(orient="records")
    except Exception:
        return []

@app.get("/api/stats/electricity")
def get_electricity_stats():
    try:
        conn = duckdb.connect()
        conn.execute("PRAGMA memory_limit='1GB'; PRAGMA threads=2;")
        query = """
            SELECT 
                CASE 
                    WHEN electricity_kwh < 10 THEN 'Low (<10 kWh)'
                    WHEN electricity_kwh BETWEEN 10 AND 20 THEN 'Medium (10-20 kWh)'
                    ELSE 'High (>20 kWh)' 
                END as usage_tier,
                AVG(carbon_footprint_kg) as avg_co2
            FROM read_csv_auto('data/personal_carbon_footprint_sample.csv')
            GROUP BY usage_tier
            ORDER BY avg_co2 ASC
        """
        df = conn.execute(query).df()
        return df.to_dict(orient="records")
    except Exception:
        return []

@app.get("/api/stats/correlations")
def get_correlations():
    try:
        conn = duckdb.connect()
        conn.execute("PRAGMA memory_limit='1GB'; PRAGMA threads=2;")
        query = """
            SELECT 
                CORR(electricity_kwh, carbon_footprint_kg) as elec_corr,
                CORR(distance_km, carbon_footprint_kg) as dist_corr,
                CORR(screen_time_hours, carbon_footprint_kg) as screen_corr
            FROM read_csv_auto('data/personal_carbon_footprint_sample.csv')
        """
        df = conn.execute(query).df()
        res = df.to_dict(orient="records")[0]
        return {
            "electricity": round(res["elec_corr"], 2),
            "distance": round(res["dist_corr"], 2),
            "screen_time": round(res["screen_corr"], 2)
        }
    except Exception:
        return {"electricity": 0, "distance": 0, "screen_time": 0}

@app.get("/api/stats/baseline")
def get_baseline_stats():
    try:
        conn = duckdb.connect()
        conn.execute("PRAGMA memory_limit='1GB'; PRAGMA threads=2;")
        query = """
            SELECT AVG(carbon_footprint_kg) as baseline_co2
            FROM read_csv_auto('data/personal_carbon_footprint_sample.csv')
        """
        df = conn.execute(query).df()
        return df.to_dict(orient="records")[0]
    except Exception:
        return {"baseline_co2": 0}

@app.get("/api/data/download")
def download_data():
    return FileResponse("data/personal_carbon_footprint_sample.csv", media_type="text/csv", filename="yeti_carbon_sample.csv")

@app.get("/api/data/preview")
def preview_data():
    try:
        conn = duckdb.connect()
        conn.execute("PRAGMA memory_limit='1GB'; PRAGMA threads=2;")
        query = "SELECT * FROM read_csv_auto('data/personal_carbon_footprint_sample.csv') LIMIT 5"
        df = conn.execute(query).df()
        # Convert NaN/float to strings or None to avoid JSON serialization errors if any exist
        return df.fillna("").to_dict(orient="records")
    except Exception:
        return []

@app.get("/")
def serve_dashboard():
    with open("src/frontend/components/dashboard.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)
