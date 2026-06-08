# Technical Architecture Document (TAD)

## 1. Technology Stack
- **Interface**: Local Python CLI / Agentic Environment
- **Backend**: Standard Python 3.11+ (AsyncIO)
- **Validation**: Pydantic
- **In-Memory Transport**: PyArrow
- **Database**: DuckDB (Embedded, Memory Capped, WAL enabled)

## 2. Architecture Principles
- **Backend Only**: Strict focus on data engineering and AI agentic architecture.
- **Minimalism & Fault Tolerance**: Avoid distributed complexity. Pipelines must fail gracefully.
- **Idempotency**: Use `INSERT OR REPLACE` to prevent duplicate records on pipeline restarts.
- **Single Node Efficiency**: Run on a single node to comply with strict 10MB repository size limits.

## 3. Directory Structure
- `src/bronze/` - Raw async data ingestion.
- `src/silver/` - Data validation and enrichment.
- `src/gold/` - Analytical aggregations.
- `src/models/` - Pydantic schemas (e.g., `CarbonActivity`).
- `data/` - Git-ignored folder containing raw JSON, `yeti.duckdb`, and `quarantine.parquet`.

## 4. Pipeline Flow
`Raw Async Data -> Pydantic Validation -> [If Fail: Parquet DLQ] -> Enrichment -> PyArrow Table -> DuckDB`
