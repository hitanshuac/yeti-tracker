# Technical Architecture Document (TAD)

## 1. Technology Stack
- **Frontend**: React/Vite Single Page Application (Glassmorphism Dashboard)
- **Backend**: Standard Python 3.11+ (AsyncIO)
- **Validation**: Pydantic
- **In-Memory Transport**: PyArrow
- **Database**: DuckDB (Embedded, Memory Capped, WAL enabled)

## 2. Architecture Principles
- **Full-Stack Showcase**: Frontend UI is explicitly included to ensure high-fidelity presentation for evaluation.
- **Minimalism & Fault Tolerance**: Avoid distributed complexity. Pipelines must fail gracefully.
- **Idempotency**: Use `INSERT OR REPLACE` to prevent duplicate records on pipeline restarts.
- **Single Node Efficiency**: Run on a single node to comply with strict 10MB repository size limits.

## 3. Directory Structure
- `src/frontend/` - React/Vite UI dashboard.
- `src/bronze/` - Raw async data ingestion.
- `src/silver/` - Data validation and enrichment.
- `src/gold/` - Analytical aggregations.
- `src/models/` - Pydantic schemas.
- `data/` - Git-ignored folder containing raw JSON, `yeti.duckdb`, and `quarantine.parquet`.

## 4. Pipeline Flow
`Frontend UI -> Async Generator -> Pydantic Validation -> [If Fail: Parquet DLQ] -> Enrichment -> PyArrow Table -> DuckDB`
