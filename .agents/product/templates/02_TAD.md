# Technical Architecture Document (TAD)

## 1. Technology Stack
- **Language**: Standard Python 3.11+
- **Validation**: Pydantic
- **In-Memory Transport**: PyArrow
- **Database**: DuckDB (Embedded, Memory Capped, WAL enabled)

## 2. Architecture Principles
- **Minimalism & Fault Tolerance**: Avoid distributed complexity. Pipelines must fail gracefully.
- **Idempotency**: Use `INSERT OR REPLACE` to prevent duplicate records on pipeline restarts.
- **Single Node Efficiency**: Run on a single node to comply with strict 10MB repository size limits and local execution capabilities.

## 3. Directory Structure
- `src/models/` - Pydantic schemas (e.g., `CarbonActivity`).
- `src/ingestion/` - Logic for PyArrow conversion and DuckDB insertion.
- `src/capabilities/` - Agentic capabilities (e.g., `git_manager.py`).
- `data/` - Git-ignored folder containing `yeti.duckdb` and `quarantine.parquet`.

## 4. Pipeline Flow
`Raw Dict -> Pydantic Validation -> [If Fail: Parquet DLQ] -> PyArrow Table -> DuckDB`
