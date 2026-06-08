# 05_TICKETS: Actionable Backlog

## Phase 1: V1 Data Science MVP (COMPLETED)
- `[x]` **TKT-001**: Scaffold FastAPI and serve static HTML dashboard.
- `[x]` **TKT-002**: Clean Kaggle dataset and ingest via DuckDB `read_csv_auto`.
- `[x]` **TKT-003**: Implement `/api/stats/diet` and `/api/stats/transport`.
- `[x]` **TKT-004**: Implement mathematical EDA queries for Pearson Correlations.
- `[x]` **TKT-005**: Overhaul UI to display glassmorphism Correlation Scorecards and horizontal bar charts.

## Phase 2: Post-Hackathon Scalability (TODO)
- `[ ]` **TKT-006: Add Geographical Filtering**
  - Extract country/region from the dataset and allow users to filter correlations by geography (e.g., does Electricity impact footprint more in the US vs India?).
- `[ ]` **TKT-007: Machine Learning Prediction Model**
  - Train a lightweight `scikit-learn` Ridge Regression model to predict future footprint based on the user's historical habits.
  - Expose via `/api/predict` endpoint.
- `[ ]` **TKT-008: Automated Report Generation**
  - Use Python to generate a PDF summary of the user's correlation metrics for offline viewing.
