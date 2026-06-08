# Product Requirements Document (PRD)

## 1. Product Overview
**Name**: Yeti-Tracker
**Vertical**: Carbon Footprint Tracking Assistant
**Goal**: A minimalist, backend-focused data ingestion pipeline that allows individuals to track and reduce their carbon footprint through simple actions.

## 2. Target Audience
Individuals tracking daily carbon-emitting activities (e.g., transportation, electricity usage). Downstream analytics tools/dashboards that will consume the clean data.

## 3. Scope & MVP
- **In Scope**: A "Bronze" ingestion layer. Validation of raw data, quarantining invalid records to a Dead Letter Queue (DLQ), and storing valid records idempotently in an embedded DuckDB database.
- **Out of Scope**: Frontend UI, complex distributed analytics (Spark/Airflow), machine learning inference.

## 4. Key Workflows
1. User/System submits raw activity data.
2. System validates data against strict schemas.
3. System routes valid data to DuckDB.
4. System routes invalid data to Parquet DLQ.
