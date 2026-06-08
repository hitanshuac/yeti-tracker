# Yeti Tracker API/UI Test Plan

This test plan is generated per the `test-automation.md` workflow to validate the FastAPI server and UI rendering.

## Framework
- **Language**: Python 3.11+
- **Test Runner**: Pytest
- **Web Client**: FastAPI TestClient (`httpx`)

## Test Cases

### 1. UI Rendering Tests
- **Test Name**: `test_serve_dashboard`, `test_serve_ingestion`, `test_serve_quarantine`
- **Type**: Integration
- **Setup**: Initialize `TestClient` with `src.main.app`.
- **Action**: Perform `GET` requests to `/`, `/ingestion`, and `/quarantine`.
- **Assertion**: Expect HTTP 200 OK. Expect response `text/html`. Verify HTML body contains specific identifying strings (e.g. "Yeti Carbon Tracker").

### 2. Dashboard Metrics API
- **Test Name**: `test_api_dashboard_metrics`
- **Type**: Integration
- **Setup**: Mock `get_category_footprint` and DuckDB/Parquet interactions.
- **Action**: `GET /api/dashboard-metrics`.
- **Assertion**: Expect HTTP 200 OK. Expect JSON payload containing `display_emissions`, `emissions_unit`, `active_scopes`, `quarantine_items`, and `data_health`.

### 3. Category Footprint API
- **Test Name**: `test_api_category_footprint`
- **Type**: Unit/Integration
- **Setup**: Mock `get_category_footprint`.
- **Action**: `GET /api/category-footprint`.
- **Assertion**: Expect HTTP 200 OK. Expect JSON list of categories.

### 4. Quarantine Feed API
- **Test Name**: `test_api_quarantine_data`
- **Type**: Integration
- **Setup**: Mock `os.path.exists` to return False (Empty state) or True with mocked Parquet Table.
- **Action**: `GET /api/quarantine-data`.
- **Assertion**: Expect HTTP 200 OK. Expect empty list if no DLQ, or valid JSON array of failed transactions.

### 5. Ingestion Feed API
- **Test Name**: `test_api_ingestion_feed`
- **Type**: Integration
- **Setup**: Mock DuckDB and Parquet returns.
- **Action**: `GET /api/ingestion-feed`.
- **Assertion**: Expect HTTP 200 OK. Verify JSON contains mixed array of `Passed` and `Quarantined` records sorted by timestamp.
