# Yeti-Tracker: Handover Document

## Project Status: COMPLETED
The Yeti-Tracker has successfully completed the Hack2Skill Challenge 3 sprint. The application pivoted from an AWS SRE Engine to a highly engaging, gamified **Personal Carbon Footprint Tracker**.

## The Gamified Pivot
The current architecture relies on a **Hybrid LLM Pipeline**:
1. **Ingestion**: The user types a natural language diary. Groq parses it into 5 integer values.
2. **Verification Gate**: These values populate explicit UI sliders so the user can verify them. This isolates LLM non-determinism from the math engine.
3. **Dual-Mode Calculation**: DuckDB processes the data dynamically. If in "Daily Mode", it compounds the daily values into a 365-day forecast. In "Yearly Mode", it bypasses the multiplier for realistic accounting.
4. **The Gamification Override**: The app visualizes Godzilla, Yeti, and Vegeta tiers based on the footprint's severity.
5. **Yeti Advisor (RAG Enabled)**: A secondary LLM dynamically roasts the user by injecting scientifically accurate DuckDB FTS Context vectors to prevent hallucinated advice.

## Important Context for Future Agents
- Do **NOT** remove the UI sliders. The architecture explicitly decoupled the LLM parsing from the DuckDB math to preserve idempotency and strict `f(x)=y` scientific validation.
- Do **NOT** modify Streamlit widget bound values outside of the `on_click` event loop handlers (`handle_extract`, `handle_calculate`). Direct assignment will trigger a `StreamlitAPIException`.
- All product templates (`.agents/product/templates/`) and ADRs (`.agents/architecture/adrs/`) accurately reflect this final state.

## Missing/Future Capabilities
- **Database Expansion**: Currently, DuckDB performs simple math. It could be expanded to run `CROSS JOINS` against real EPA datasets for precise regional electricity tracking if the user inputs their zip code.
- **Vision Models**: If API limits relax, the static `yeti_alert.png` could be replaced by dynamic Generative AI outputs based on the exact severity of the footprint.
