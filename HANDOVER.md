# Handover Document

## System State
The Yeti-Tracker Bronze Ingestion Pipeline has been successfully scaffolded and tested.
- **Ingestion**: Pydantic validation -> PyArrow Table -> DuckDB `INSERT OR REPLACE`
- **Quarantine**: Failed records are routed to `quarantine_activities.parquet`.
- **Database**: DuckDB is running with strict memory limits and WAL.

## Active Rules & Workflows
All 10MB constraints and single-branch `main` rules are enforced.
The `master-sync.md` workflow serves as the primary orchestrator.
