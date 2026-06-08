# Product Requirements Document (PRD)

## 1. Product Overview
**Name**: Yeti-Tracker
**Vertical**: Carbon Footprint Tracking Assistant
**Goal**: A backend-focused, production-grade agentic solution that helps track and reduce carbon footprints through a local Medallion Architecture.

## 2. Target Audience
Developers tracking daily carbon-emitting activities via an agentic CLI/Backend interface.

## 3. Scope & MVP
- **In Scope**: A "Bronze, Silver, Gold" ingestion backend layer. Validation of raw data, quarantining invalid records to a Dead Letter Queue (DLQ), and storing valid records idempotently in an embedded DuckDB database.
- **Out of Scope**: Frontend UI. Complex distributed analytics orchestrators (Spark/Airflow).

## 4. Key Workflows
1. Bronze layer generates asynchronous mock transaction data.
2. Silver layer cleans and validates data against strict schemas, routing invalid data to a Parquet DLQ.
3. Silver layer enriches data via static MCC mappings.
4. Gold layer aggregates data into final reporting tables.
