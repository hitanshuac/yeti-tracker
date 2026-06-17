# Yeti-Tracker: Personal Carbon Footprint Gamification 🌍

**Vertical/Persona:** "Carbon Footprint Awareness Platform" (Hack2Skill Challenge 3)

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![DuckDB](https://img.shields.io/badge/duckdb-embedded-yellow.svg)
![Streamlit](https://img.shields.io/badge/streamlit-UI-red.svg)

## Overview: The Hybrid LLM Pipeline

Yeti-Tracker is an AI-powered personal carbon footprint platform that completely reimagines how individuals understand their environmental impact. Rather than a boring calculator, Yeti-Tracker is an emotional, gamified, cognitive mirror that classifies your daily habits into visceral visual metaphors.

To solve the inherent conflict between **AI Hallucinations** (non-determinism) and **Scientific Data Integrity** (idempotent mathematics), Yeti-Tracker implements the **Hybrid Pipeline** (Split-Plane Architecture):

1. **The Confessional (LLM Ingestion)**: Users paste a messy, natural language diary entry.
2. **The Verification Gate**: The LLM *only* populates explicit UI sliders. The human verifies the extracted integers, guaranteeing the AI cannot break the downstream math.
3. **The 365-Day Forecaster**: A local DuckDB instance takes the verified seed day and compounds it deterministically across a 365-day year.
4. **The "Over 9000" Gamification**: If the footprint crosses 9,000kg (average global citizen), the UI violently shatters, flashing a "GODZILLA FOOTPRINT DETECTED: IT'S OVER 9000" meme.
5. **The Yeti Advisor**: Finally, a second LLM dynamically generates a sarcastic, aggressive roasting from the perspective of a melting Yeti.

## Dynamic Skill Integration
The Yeti-Tracker's intelligence is powered by composable skill imports located in `.agents/skills/`. This allows the agent to dynamically load capabilities such as pipeline architecture, diagram generation, or running an LLM-Council debate without cluttering the core application logic.

## Installation & Setup

```bash
git clone https://github.com/hitanshuac/yeti-tracker.git
cd yeti-tracker
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Running the Dashboard Locally
We strictly follow 12-Factor App methodology for secrets. We have provided a template for you.
1. Open `.secrets/.env` and add your **GROQ_API_KEY**.
2. Run the convenience batch script to automatically start the Dashboard.

```bash
run_server.bat
# Automatically opens in your browser!
```

## Current Capabilities

Yeti-Tracker enforces strict engineering standards via the `.agents` framework. This is a dynamic inventory based on the current stable checkpoint:

- **Rules (18 Active)**: Including `defensive-programming.md`, `code-quality-standards.md`, `sre-sop.md`, and `12-factor-rules.md`.
- **Python APIs**: Built with Streamlit, Plotly, DuckDB, and Pydantic with idempotent I/O and strict error observability.
- **Product Templates (5 Active)**: Fully populated `01_PRD.md`, `02_TAD.md`, `03_SECURITY.md`, `04_FRONTEND.md`, and `05_TICKETS.md`.
- **Skills (5 Active)**: Diagram Generator, DuckDB Optimizer, LLM-Council, Pipeline Architect, Universal Ingestion.
- **Workflows (23 Active)**: Including `master-sync.md`, `test-automation.md`, and `update-docs.md`.
- **Architecture Decision Records (3 Active)**: Latest is ADR-0003 for the Master Sync Checkpoint.

## Directory Structure

- `src/`: Core logic and capabilities (e.g., `git_manager.py`, `observability.py`).
- `data/`: Local storage for `yeti.duckdb`, CSV baselines, and `error_logs.json`.
- `.agents/`: Governance rules, product templates, agentic skills, and autonomous workflows.
- `.antigravity/`: (Legacy reference; currently scrubbed in favor of `.agents/`).

## Adoption Method
To inject the Agentic Brain into other projects, simply copy the `.agents/` directory to the root of your new project and invoke the `bootstrap.md` or `master-sync.md` workflows.

## Visual Reference Appendix
*(Diagrams skipped during this sync pass to preserve existing structural baselines)*
<p align="center">
  <img src="data/assets/yeti_alert.png" width="400" />
  <img src="data/assets/godzilla_over_9000.png" width="400" />
</p>

## Acknowledgments
Credit to the study `antigravity` repository for the base templates and agentic workflows.
