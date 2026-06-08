# Yeti-Tracker: Deep Dive EDA Data Science Engine 🌍
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![DuckDB](https://img.shields.io/badge/duckdb-embedded-yellow.svg)

## Executive Summary: A Data-Driven Strategy
*Prepared by: Principal Engineer Antigravity for the PromptWars Board of Directors.*

Yeti-Tracker is a purely analytical, client-side data science showcase. Moving far beyond generic operational tracking, it acts as a "Deep Dive EDA Engine" that uses mathematical correlations (Pearson coefficients) to visually debunk common myths around personal carbon footprints.

### The PACE Framework (Data Strategy)
In strict alignment with Google Data Analytics professional standards, our data lifecycle follows the **PACE** methodology (Plan, Analyze, Construct, Execute). 
- 📊 **[Read the Full Data Analysis Showcase Here](docs/data_analysis_showcase.md)**

## The MVP Pivot
Initially designed as an operational data pipeline (with Dead Letter Queues and Pydantic validation), our deep dive into the Kaggle dataset revealed that simple dashboards are ineffective. We pivoted the architecture to a pure **Exploratory Data Analysis (EDA) Showcase**.

### Key Findings We Proved:
1. **The Walking Paradox**: Walking generates 0 emissions, but high-impact diets and electricity usage completely eclipse the savings from walking.
2. **The Screen Time Myth**: We proved mathematically that screen time has *zero correlation* (-0.03) with an individual's carbon footprint.
3. **The Real Culprits**: Electricity usage (0.42 correlation) and Non-Veg diets are the true massive predictors of CO2 output.

## Approach and Architecture
We utilize a minimalist **Split-Plane Architecture** featuring a production-grade Vanilla UI, backed by standard Python and DuckDB.

1. **Frontend UI**: A fully accessible, dark-glassmorphism dashboard that visually charts our EDA findings without requiring user logins.
2. **DuckDB Analytics Engine**: Instead of bloated ETL streams, we use DuckDB's in-memory `read_csv_auto` to instantly query the Kaggle dataset and perform heavy aggregations (like calculating Pearson Correlations in milliseconds).
3. **Control Plane (`.agents/`)**: The Antigravity Brain enforcing Hack2Skill constraints and autonomous workflows.

## Installation & Setup
```bash
git clone https://github.com/hitanshuac/yeti-tracker.git
cd yeti-tracker
python -m venv venv
venv\Scripts\activate
pip install duckdb fastapi uvicorn httpx pandas
```

### Running the Dashboard Locally
```bash
python -m uvicorn src.main:app --reload
# Navigate to http://localhost:8000
```

## Directory Structure
- `src/`: Main application source code and FastAPI endpoints.
- `data/`: Kaggle dataset and generated metadata.
- `.agents/`: Governance rules, product templates, agentic skills, and autonomous workflows.

## Adoption Method
To adopt the Agentic Brain in other projects, seamlessly copy the `.agents/` directory into your repository and run the `master-sync.md` workflow to initialize the governance layer and establish the autonomous CI/CD bridge.

## Acknowledgments
Credit to the study antigravity repository for the agentic constraints framework.