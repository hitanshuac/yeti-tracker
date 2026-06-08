# 01_PRD: Yeti-Tracker EDA Showcase

## 1. Product Vision
Yeti-Tracker is a purely analytical, client-side data science showcase. Moving beyond operational tracking, it acts as a "Deep Dive EDA Engine" that uses mathematical correlations (Pearson coefficients) to visually debunk common myths around personal carbon footprints.

## 2. Target Audience
- Data Scientists and Hackathon Judges (specifically for the Hack2Skill PromptWars).
- Individuals looking for scientifically backed, high-yield behavioral changes rather than generic "eco-friendly" advice.

## 3. Core Features (MVP)
- **Direct Kaggle Ingestion**: Seamlessly reads raw CSV behavioral data via DuckDB without heavy ETL abstractions.
- **Diet Impact Analysis**: Aggregates average daily carbon footprint by diet type (Veg, Non-Veg, Mixed).
- **Transport Impact Analysis**: Aggregates footprint by transport mode to identify the "Walking Paradox" (where diet eclipses local transport savings).
- **Mythbusting Correlations**: Calculates exact Pearson correlations for Electricity (Strong Predictor) vs Screen Time (Zero Impact).

## 4. Non-Goals
- Real-time banking integration or OAuth.
- Cloud data warehousing (must remain 100% local).
- Operational CRUD (Create, Read, Update, Delete) workflows.

## 5. Success Metrics
- Analytical query latency under 500ms via DuckDB.
- Repository footprint strictly under 10MB.
- UI explicitly highlights the two major EDA findings (Diet and Electricity).
