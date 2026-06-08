# Actionable Backlog

## Ticket 1: Core Scaffolding & CI/CD Setup
- **Objective**: Set up the Python project structure, `.gitignore`, and `pytest`.
- **Acceptance Criteria**:
  - `data/`, `src/models/`, `src/ingestion/`, and `tests/` directories exist.
  - `.gitignore` explicitly ignores `data/`, `__pycache__`, and `.pytest_cache`.
  - `pytest` runs successfully (even if empty).

## Ticket 2: Implement `CarbonActivity` Model
- **Objective**: Create the strict Pydantic validation schema.
- **Acceptance Criteria**:
  - Model has `activity_id` (UUID), `user_id` (str), `activity_type` (str), `carbon_kg` (float), and `timestamp` (datetime).
  - Validation fails if `carbon_kg` is negative.

## Ticket 3: PyArrow & DuckDB Ingestion
- **Objective**: Implement the idempotent DuckDB insertion logic.
- **Acceptance Criteria**:
  - A function accepts a list of valid `CarbonActivity` objects.
  - Converts them to a PyArrow Table.
  - Idempotently (`INSERT OR REPLACE`) writes them to `data/yeti.duckdb`.
  - DuckDB is configured with WAL and memory limits.

## Ticket 4: Dead Letter Queue (DLQ) Implementation
- **Objective**: Route invalid records to a Parquet file.
- **Acceptance Criteria**:
  - A processing function attempts validation.
  - Invalid dicts are caught and appended to `data/quarantine_activities.parquet`.
  - Valid dicts proceed to DuckDB.

## Ticket 5: Git Manager Capability
- **Objective**: Implement `src/capabilities/git_manager.py` for the Secure Checkpoint workflow.
- **Acceptance Criteria**:
  - Script accepts a commit message.
  - Stages all allowed files.
  - Commits with the message.
  - Pushes to `main`.
