# Yeti Tracker UI/Engine Test Plan

This test plan is generated per the `test-automation.md` workflow to validate the Streamlit UI state management and DuckDB deterministic math engine.

## Framework
- **Language**: Python 3.11+
- **Test Runner**: Pytest
- **Coverage Goal**: > 80%

## Test Cases

### 1. `src/state_manager.py`
- **Type**: Unit
- **Setup**: Clean `dict` to simulate `st.session_state`.
- **Action/Assertion**:
  - `test_init_state_empty`: Verify `init_state` populates all default `AppState` fields safely without wiping existing keys.
  - `test_init_state_existing`: Verify `init_state` preserves existing keys in `st.session_state`.
  - `test_get_state`: Verify `get_state` successfully reads from `st.session_state` and returns a valid `AppState` Pydantic model.

### 2. `src/history.py`
- **Type**: Unit / Integration
- **Setup**: Isolated temp file `tests/fixtures/temp.duckdb`.
- **Action/Assertion**:
  - `test_append_history_valid`: Verify `append_history` writes a row correctly.
  - `test_append_history_invalid`: Verify negative CO2 outputs or empty session IDs raise `ValueError` (Defensive Programming Rule 4).
  - `test_fetch_historical_kpis`: Verify KPI strings handle both empty and populated datasets.
  - `test_fetch_history_dataframe`: Verify `fetch_history_dataframe` returns a correctly shaped Pandas DataFrame.
  - `test_seed_demo_history`: Verify the seeder successfully populates 30 days of data.

### 3. `src/chart_factory.py`
- **Type**: Unit
- **Action/Assertion**:
  - `test_create_gauge_chart`: Verify it returns a `go.Figure` object with the correct type.
  - `test_create_savings_waterfall`: Verify it returns a `go.Figure` and handles zero savings correctly.
  - `test_create_doom_vs_rescue`: Verify it builds the 12-month projection figure.
  - `test_create_history_chart`: Verify it processes the rolling 7-day average correctly from a mock DataFrame.

### 4. `src/carbon_engine.py`
- **Type**: Unit
- **Action/Assertion**:
  - `test_anomaly_detection`: Explicitly test `_detect_anomaly` and `_log_engine_error` exception paths.
  - `test_classify_tier`: Cover the edge cases for tier thresholds (0, 15000, 30000+).

### 5. `src/llm_service.py`
- **Type**: Unit / Integration
- **Setup**: Mock `groq.Groq` to prevent actual API calls.
- **Action/Assertion**:
  - `test_parse_confession_error_handling`: Mock API failures (`GroqError`, `RateLimitError`) to trigger the fallback logic and error logger.
  - `test_get_advisor_response_success`: Mock successful advisor JSON parsing.
  - `test_get_advisor_response_fallback`: Mock a completely broken LLM response to ensure it falls back gracefully without crashing.
