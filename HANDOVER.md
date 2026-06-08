# Handover Document

## System State
The Yeti-Tracker has pivoted from an operational data pipeline to a **Pure EDA Data Science Engine**.
- **Execution**: DuckDB `read_csv_auto` natively analyzes the `personal_carbon_footprint_sample.csv`.
- **Validation**: FastAPI securely exposes these analytical groupings (Diet, Transport) and math metrics (Pearson Correlations) via `/api/stats/*`.
- **Presentation**: A dark-glassmorphism Tailwind UI visually debunks the "Screen Time" myth and highlights Electricity usage.

## Active Rules & Workflows
- All cache files have been purged to ensure strict 10MB limits.
- The repository follows a Split-Plane Architecture, where the `.agents/` folder serves as the permanent Control Plane and PromptWars Brain.
- The `master-sync.md` workflow serves as the primary orchestrator.
