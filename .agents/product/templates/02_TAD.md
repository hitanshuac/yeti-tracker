# 02_TAD: Technical Architecture Design

## 1. System Overview
The Yeti-Tracker employs a **Split-Plane Architecture** featuring a pure Data Science Execution Plane powered by DuckDB, overseen by the Antigravity Control Plane (`.agents/`).

## 2. Component Architecture
- **Control Plane (`.agents/`)**: Houses the Hack2Skill constraints, workflows, and prompts.
- **Data Layer (DuckDB)**: Embedded OLAP engine utilizing `read_csv_auto` to instantly query the synthetic Kaggle dataset (`data/personal_carbon_footprint_sample.csv`).
- **Backend (FastAPI)**: A lightweight Python web server exposing analytical aggregations:
  - `/api/stats/diet`
  - `/api/stats/transport`
  - `/api/stats/electricity`
  - `/api/stats/correlations`
- **Frontend (Vanilla HTML/JS + Tailwind)**: A glassmorphism dashboard utilizing native `fetch()` to render visual validation panels and scorecards.

## 3. Technology Stack
- **Database**: DuckDB (Embedded, In-Memory processing)
- **Backend**: FastAPI, Uvicorn
- **Frontend**: HTML5, Tailwind CSS, Vanilla JS
- **Data**: Synthetic Kaggle CSV (`personal_carbon_footprint_sample.csv`)

## 4. Data Flow
1. **Request**: UI triggers `fetchMetrics()`.
2. **Process**: FastAPI executes DuckDB SQL against the raw CSV.
3. **Analyze**: DuckDB calculates Pearson correlations and groupings.
4. **Respond**: FastAPI returns JSON arrays.
5. **Render**: UI dynamically draws horizontal data bars based on the relative scale of the `avg_co2` values.

## 5. Architectural Constraints
- **Zero-State ETL**: Eliminated PyArrow Dead Letter Queues and `INSERT` logic. Data is treated immutably at read-time.
- **Size**: Repository must not exceed 10MB. 
