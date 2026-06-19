# Yeti-Tracker: Handover Document

## Project Status: COMPLETED
The Yeti-Tracker has successfully completed the Hack2Skill Challenge 3 sprint. The application pivoted from an AWS SRE Engine to a highly engaging, gamified **Indian Carbon Footprint Tracker**.

## The Gamified Pivot
The application was recently refactored from an 851-line `app.py` monolith into a cleanly separated 6-module architecture (`state_manager`, `carbon_engine`, `llm_service`, `rag_service`, `chart_factory`, `history`). It relies on a **Hybrid LLM Pipeline**:
1. **Continuous Confessional**: The user types a natural language diary. `llm_service.py` parses it into 5 integer values (km, hours, meals). The Yeti Advisor's responses append into the UI, creating an addictive loop.
2. **Regex Math Interceptor**: When the LLM hallucinates mathematical expressions (e.g., `260 * 2`) instead of computing them, `_recover_failed_generation` natively evals the math before passing it to the Verification Gate.
3. **Verification Gate**: These values populate explicit UI sliders so the user can verify them. This isolates LLM non-determinism from the math engine.
4. **Deterministic Engine**: `carbon_engine.py` using DuckDB processes the data dynamically, tracking the user's trajectory persistently via UUID session tracking in `history.py`. It generates an exact tax penalty using the Indian Social Cost of Carbon (₹15.80/kg).
5. **The Gamification Override**: The app visualizes Category 3 Catastrophes based on the footprint's severity with visual assets.
6. **Smart Yeti Advisor**: A secondary LLM dynamically analyzes the user's largest un-optimized lifestyle category to deliver guaranteed, non-redundant mitigation strategies.

## Important Context for Future Agents
- Do **NOT** remove the UI sliders. The architecture explicitly decoupled the LLM parsing from the DuckDB math to preserve idempotency and strict `f(x)=y` scientific validation.
- Do **NOT** modify Streamlit widget bound values outside of the `on_click` event loop handlers (`handle_extract`, `handle_calculate`, `handle_reply`). Direct assignment will trigger a `StreamlitAPIException`.
- All product templates (`.agents/product/templates/`) and ADRs (`.agents/architecture/adrs/`) accurately reflect this final state.

## Missing/Future Capabilities
- **Database Expansion**: Currently, DuckDB performs simple math. It could be expanded to run `CROSS JOINS` against real EPA datasets for precise regional electricity tracking if the user inputs their zip code.
- **Vision Models**: If API limits relax, the static `yeti.jpg` could be replaced by dynamic Generative AI outputs based on the exact severity of the footprint.
