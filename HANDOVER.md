# Yeti-Tracker: Handover Document

## Project Status: COMPLETED
The Yeti-Tracker has successfully completed the Hack2Skill Challenge 3 sprint. The application pivoted from an AWS SRE Engine to a highly engaging, gamified **Personal Carbon Footprint Tracker**.

## The Gamified Pivot
The current architecture relies on a **Hybrid LLM Pipeline**:
1. **Ingestion**: The user types a natural language diary. Groq parses it into 3 integer values.
2. **Verification Gate**: These values populate explicit UI sliders so the user can verify them. This isolates LLM non-determinism from the math engine.
3. **Calculation**: DuckDB compounds the daily values into a 365-day forecast.
4. **The Over 9000 Override**: If the forecast > 9000kg, the standard UI gauges shatter, displaying `godzilla_over_9000.png`.
5. **Yeti Advisor**: A secondary LLM dynamically roasts the user's specific inputs and offers reduction advice.

## Important Context for Future Agents
- Do **NOT** remove the UI sliders. The architecture explicitly decoupled the LLM parsing from the DuckDB math to preserve idempotency and strict `f(x)=y` scientific validation.
- All product templates (`.agents/product/templates/`) and ADRs (`.agents/architecture/adrs/`) accurately reflect this final state.
- If you need to test the "Over 9000" Godzilla state, simply set "Miles Driven" to 500 in the UI and click run.

## Missing/Future Capabilities
- **Database Expansion**: Currently, DuckDB performs simple math. It could be expanded to run `CROSS JOINS` against real EPA datasets for precise regional electricity tracking if the user inputs their zip code.
- **Vision Models**: If API limits relax, the static `yeti_alert.png` could be replaced by dynamic Generative AI outputs based on the exact severity of the footprint.
