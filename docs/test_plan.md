# Yeti Tracker UI/Engine Test Plan

This test plan is generated per the `test-automation.md` workflow to validate the deterministic math engine's persistence logic.

> [!WARNING]
> Due to the extreme < 8-hour Hack2Skill deadline constraints, full Test-Driven Development (TDD) across all modules was scoped down. The automated test coverage focuses strictly on the most critical component: the DuckDB integration and schema-resilient persistence layer.

## Framework
- **Language**: Python 3.11+
- **Test Runner**: Pytest
- **Primary Focus**: Data Integrity & Idempotency (SRE Inner Loop)

## Test Cases

### 1. `src/history.py` (DuckDB Persistence Layer)
- **Type**: Unit / Integration
- **Setup**: Isolated temp file `tests/fixtures/temp.duckdb`.
- **Action/Assertion**:
  - `test_append_history_valid`: Verify `append_history` writes a row correctly using dynamic explicit column mapping.
  - `test_append_history_invalid`: Verify negative CO2 outputs or empty session IDs raise `ValueError` (Defensive Programming Rule 4).
  - `test_fetch_historical_kpis`: Verify KPI strings handle both empty and populated datasets without crashing.
  - `test_fetch_history_dataframe`: Verify `fetch_history_dataframe` returns a correctly shaped Pandas DataFrame for Plotly.
  - `test_seed_demo_history`: Verify the seeder successfully populates 30 days of data deterministically.
  - `test_legacy_schema_migration`: Verify the startup hook uses `PRAGMA table_info` to perform safe, idempotent ALTER TABLE migrations without data loss (Defensive Programming Rule 1).

## Deprecated Stubs Removed
All other `test_*.py` stubs that previously existed to artificially inflate perceived coverage were purged during the Final Agentic Refactor checkpoint to strictly comply with Code Quality and SAST honesty standards.
