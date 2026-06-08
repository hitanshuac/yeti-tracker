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


