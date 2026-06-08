from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pandas as pd

from src.main import app

client = TestClient(app)

def test_serve_dashboard():
    """Verify the root endpoint serves the dashboard HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "Yeti Carbon Tracker - Dashboard" in response.text

def test_serve_ingestion():
    """Verify the /ingestion endpoint serves the ingestion HTML."""
    response = client.get("/ingestion")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "Live Validation Feed" in response.text

def test_serve_quarantine():
    """Verify the /quarantine endpoint serves the quarantine HTML."""
    response = client.get("/quarantine")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert "Dead Letter Queue" in response.text

@patch("src.main.get_category_footprint")
def test_api_dashboard_metrics(mock_get_category_footprint):
    """Verify the metrics API returns the correct JSON format."""
    mock_get_category_footprint.return_value = [
        {"category": "Flight", "total_carbon_kg": 1500.5, "total_transactions": 2}
    ]
    
    response = client.get("/api/dashboard-metrics")
    assert response.status_code == 200
    data = response.json()
    
    assert data["display_emissions"] == "1.5k"
    assert data["emissions_unit"] == "tCO2e"
    assert "active_scopes" in data
    assert "quarantine_items" in data
    assert "data_health" in data
    assert "data_health_width" in data

@patch("src.main.get_category_footprint")
def test_api_category_footprint(mock_get_category_footprint):
    """Verify the category footprint API passes data correctly."""
    mock_data = [{"category": "Flight", "total_carbon_kg": 150.0, "total_transactions": 1}]
    mock_get_category_footprint.return_value = mock_data
    
    response = client.get("/api/category-footprint")
    assert response.status_code == 200
    assert response.json() == mock_data

@patch("src.main.os.path.exists")
def test_api_quarantine_data_empty(mock_exists):
    """Verify quarantine data returns empty list when no DLQ file exists."""
    mock_exists.return_value = False
    
    response = client.get("/api/quarantine-data")
    assert response.status_code == 200
    assert response.json() == []

@patch("src.main.pq.read_table")
@patch("src.main.os.path.exists")
def test_api_quarantine_data_populated(mock_exists, mock_read_table):
    """Verify quarantine data returns proper rows when DLQ exists."""
    mock_exists.return_value = True
    
    mock_df = pd.DataFrame([{"transaction_id": "1", "timestamp": "2026-06-08 12:00:00"}])
    mock_table = MagicMock()
    mock_table.to_pandas.return_value = mock_df
    mock_read_table.return_value = mock_table
    
    response = client.get("/api/quarantine-data")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["transaction_id"] == "1"

@patch("src.main.duckdb.connect")
@patch("src.main.pq.read_table")
@patch("src.main.os.path.exists")
def test_api_ingestion_feed(mock_exists, mock_read_table, mock_duckdb_connect):
    """Verify ingestion feed properly merges passed and quarantined records."""
    mock_exists.return_value = True
    
    # Mock DuckDB for passed records
    mock_conn = MagicMock()
    mock_res = MagicMock()
    mock_res.df.return_value = pd.DataFrame([
        {"transaction_id": "T1", "timestamp": "2026-06-08 12:00:00", "mcc_code": "1111", "amount": 100.0, "status": "Passed"}
    ])
    mock_conn.execute.return_value = mock_res
    mock_duckdb_connect.return_value = mock_conn
    
    # Mock Parquet for failed records
    mock_df = pd.DataFrame([
        {"transaction_id": "T2", "timestamp": "2026-06-08 12:05:00", "mcc_code": "2222", "amount": -50.0}
    ])
    mock_table = MagicMock()
    mock_table.to_pandas.return_value = mock_df
    mock_read_table.return_value = mock_table
    
    response = client.get("/api/ingestion-feed")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 2
    # Because T2 is newer (12:05 vs 12:00), it should be first
    assert data[0]["transaction_id"] == "T2"
    assert data[0]["status"] == "Quarantined"
    assert data[1]["transaction_id"] == "T1"
    assert data[1]["status"] == "Passed"
