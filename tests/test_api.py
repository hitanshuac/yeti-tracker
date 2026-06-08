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

@patch("src.main.duckdb.connect")
def test_api_diet_stats(mock_connect):
    """Verify the diet stats API returns correct aggregations."""
    mock_conn = MagicMock()
    mock_res = MagicMock()
    mock_res.df.return_value = pd.DataFrame([{"food_type": "Vegetarian", "avg_co2": 2.5}])
    mock_conn.execute.return_value = mock_res
    mock_connect.return_value = mock_conn

    response = client.get("/api/stats/diet")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["food_type"] == "Vegetarian"

@patch("src.main.duckdb.connect")
def test_api_transport_stats(mock_connect):
    """Verify the transport stats API returns correct aggregations."""
    mock_conn = MagicMock()
    mock_res = MagicMock()
    mock_res.df.return_value = pd.DataFrame([{"transport_mode": "Walk", "avg_co2": 0.0}])
    mock_conn.execute.return_value = mock_res
    mock_connect.return_value = mock_conn

    response = client.get("/api/stats/transport")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["transport_mode"] == "Walk"

@patch("src.main.duckdb.connect")
def test_api_electricity_stats(mock_connect):
    """Verify the electricity stats API returns tiered data."""
    mock_conn = MagicMock()
    mock_res = MagicMock()
    mock_res.df.return_value = pd.DataFrame([{"usage_tier": "High (>20 kWh)", "avg_co2": 15.5}])
    mock_conn.execute.return_value = mock_res
    mock_connect.return_value = mock_conn

    response = client.get("/api/stats/electricity")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["usage_tier"] == "High (>20 kWh)"

@patch("src.main.duckdb.connect")
def test_api_correlations(mock_connect):
    """Verify the correlations API returns rounded pearson coefficients."""
    mock_conn = MagicMock()
    mock_res = MagicMock()
    mock_res.df.return_value = pd.DataFrame([{
        "elec_corr": 0.423,
        "dist_corr": 0.312,
        "screen_corr": -0.034
    }])
    mock_conn.execute.return_value = mock_res
    mock_connect.return_value = mock_conn

    response = client.get("/api/stats/correlations")
    assert response.status_code == 200
    data = response.json()
    assert data["electricity"] == 0.42
    assert data["distance"] == 0.31
    assert data["screen_time"] == -0.03
