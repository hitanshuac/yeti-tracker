# Technical Architecture Document (TAD)

## 1. System Overview
Yeti-Tracker is a Streamlit-based monolithic Python application. It leverages a Hybrid LLM pipeline (Groq), a localized embedded OLAP database (DuckDB), and robust schema validation (Pydantic) to securely manage the transition from natural language inputs to deterministic mathematical outputs.

## 2. Component Architecture
1. **Frontend (Streamlit)**: Single-page application rendering the "Confessional" text area, verification sliders, Plotly gauges, and conditional "Over 9000" image overrides.
2. **Ingestion Layer (Groq LLM + Pydantic)**: A prompt-engineered LLM (`llama-3.1-8b-instant`) extracts exactly three integers (Miles, AC, Steaks) from unstructured text and enforces them through the `ParsedPersonalData` Pydantic model.
3. **Deterministic Core (DuckDB)**: A mathematically isolated SQL engine that calculates the 365-day cumulative CO2 footprint based *only* on the verified slider inputs.
4. **Advisory Layer (Groq LLM)**: The `get_yeti_advice` function provides dynamic, gamified reduction strategies at the very end of the pipeline.
5. **Observability**: `log_error_to_json` implements a thread-safe, idempotent, strictly typed JSON error logging mechanism per Tier 0 SRE rules.

## 3. Data Flow
`User Text -> LLM JSON -> Pydantic Validation -> UI Sliders -> User Approval -> DuckDB Math -> UI Gamification -> LLM Yeti Advisor`

## 4. Dependencies
- **Core**: Python 3.11+, Streamlit
- **Data**: DuckDB, Pydantic
- **AI**: Groq API
- **Visuals**: Plotly, Custom AI-generated PNG assets.
