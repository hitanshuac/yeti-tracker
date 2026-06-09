# Handover Document

## System State
The Yeti-Tracker is a **Pure EDA Data Science Engine** built around a logical Bronze -> Silver -> Gold pipeline.
- **Execution**: DuckDB `read_csv_auto` natively analyzes the `personal_carbon_footprint_sample.csv` (Bronze).
- **Validation**: FastAPI securely exposes aggregated ESG metrics and top-level KPIs via `/api/stats/*` (Silver).
- **Presentation**: A dark-glassmorphism Tailwind UI visually displays the Enterprise Employee Carbon Overview (Gold).

## Active Rules & Workflows
- All cache files have been purged to ensure strict <10MB limits.
- The repository follows a Split-Plane Architecture, where the `.agents/` folder serves as the permanent Control Plane and PromptWars Brain.
- Strict Constraints (`01-strict-constraints.md`) and Hack2Skill rules (`02-hack2skill-rules.md`) are the absolute laws governing this codebase.

## 🤖 Antigravity Rebuild Protocol
If you are an AI Agent (Antigravity) or human engineer spawning into this repository on a new machine, follow this exact sequence to rebuild the environment:
1. **Initialize Environment**: Execute `python -m venv venv` and activate it.
2. **Install Dependencies**: Execute `pip install -r requirements.txt`. Do NOT install heavy packages outside this list to protect the 10MB limit.
3. **Verify Data**: Ensure `data/personal_carbon_footprint_sample.csv` is present.
4. **Boot Server**: Run the `run_server.bat` file to automatically boot the Uvicorn/FastAPI backend on port 8000.
5. **Run Tests**: Execute `python -m pytest tests/` to confirm the backend routing and mock endpoints are stable.
6. **Context Sync**: Immediately read `.agents/rules/01-strict-constraints.md` to understand your operational boundaries.
7. **Master Sync**: Execute the `.agents/workflows/master-sync.md` workflow. This serves as the primary orchestrator to automatically enforce governance, validate the architecture, and establish the CI/CD bridge before writing any new code.
