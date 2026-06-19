# Execution Backlog (Tickets)

All tickets for the Yeti-Tracker Hack2Skill project have been completed.

- `[x]` **TICKET-001: Establish Observability**
  - Implement Tier-0 error logging via `log_error_to_json`.
  - Enforce pre-write validation and atomic file renames.

- `[x]` **TICKET-002: LLM Ingestion Pipeline**
  - Integrate Groq (`llama-3.1-8b-instant`).
  - Write `parse_messy_text()` with strict Pydantic schema fallback logic.

- `[x]` **TICKET-003: DuckDB Math Engine**
  - Implement `run_duckdb_math()` to forecast 365-day carbon footprints and tree offsets.

- `[x]` **TICKET-004: Frontend Visuals (Normal State)**
  - Implement dark-mode Plotly Gauges via `create_gauge_fig`.

- `[x]` **TICKET-005: Gamification Pivot ("Over 9000")**
  - Generate AI image assets (`tier2_alert.png`, `tier3_alert.png`).
  - Implement dynamic UI overrides based on mathematical thresholds.

- `[x]` **TICKET-006: Human-in-the-Loop Hybrid Gate**
  - Bind LLM output to standard UI Sliders.
  - Decouple LLM hallucination risk from the DuckDB Math Engine.

- `[x]` **TICKET-007: Yeti Advisor**
  - Implement secondary LLM call (`get_yeti_advice()`) for dynamic reduction strategies.

- `[x]` **TICKET-008: Indian Carbon Engine Pivot**
  - Transition from USD/miles to INR/km based on the ₹15.80/kg Social Cost of Carbon (SCC).
  - Modify LLM extraction parsing layer to recover from mathematical expressions (Regex Evaluator).
  - Force Continuous Confession loop, updating UUID session state natively.
