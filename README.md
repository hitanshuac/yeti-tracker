# Yeti-Tracker: Personal Carbon Footprint Gamification 🌍
**Vertical/Persona:** "Carbon Footprint Awareness Platform" (Hack2Skill Challenge 3)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![DuckDB](https://img.shields.io/badge/duckdb-embedded-yellow.svg)
![Streamlit](https://img.shields.io/badge/streamlit-UI-red.svg)

## Executive Summary: The Hybrid LLM Pipeline

Yeti-Tracker is an AI-powered personal carbon footprint platform that completely reimagines how individuals understand their environmental impact. Rather than a boring calculator, Yeti-Tracker is an emotional, gamified, cognitive mirror that classifies your daily habits into visceral visual metaphors.

To solve the inherent conflict between **AI Hallucinations** (non-determinism) and **Scientific Data Integrity** (idempotent mathematics), Yeti-Tracker implements the **Hybrid Pipeline**:

1. **The Confessional (LLM Ingestion)**: Users paste a messy, natural language diary entry (e.g., "I drove 20 miles and ate a burger"). The `llama-3.1-8b-instant` LLM parses this frictionless data.
2. **The Verification Gate**: The LLM *only* populates explicit UI sliders. The human verifies the extracted integers, guaranteeing the AI cannot break the downstream math.
3. **The 365-Day Forecaster**: A local DuckDB instance takes the verified seed day and compounds it deterministically across a 365-day year, calculating total CO2 and Tree Offset Debt.
4. **The "Over 9000" Gamification**: If the footprint is sustainable, the UI remains a hyper-professional enterprise dashboard. If the footprint crosses 9,000kg (average global citizen), the UI violently shatters, flashing a "GODZILLA FOOTPRINT DETECTED: IT'S OVER 9000" meme.
5. **The Yeti Advisor**: Finally, a second LLM dynamically generates a sarcastic, aggressive roasting from the perspective of a melting Yeti, providing one actionable way to reduce the footprint.

## The Gamification Visuals
If you dare to input a massive carbon footprint, you will face the consequences:
<p align="center">
  <img src="data/assets/yeti_alert.png" width="400" />
  <img src="data/assets/godzilla_over_9000.png" width="400" />
</p>

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
Yeti-Tracker enforces strict engineering standards via the `.agents` framework.
- **Rules (18 Active)**: Including `defensive-programming.md`, `code-quality-standards.md`, `sre-sop.md`, and `12-factor-rules.md`.
- **Python Architecture**: Built with Streamlit, Plotly, DuckDB, and Pydantic with idempotent I/O and strict error observability.
- **Product Templates**: Fully populated `01_PRD.md`, `02_TAD.md`, `03_SECURITY.md`, `04_FRONTEND.md`, and `05_TICKETS.md`.
- **Workflows (23 Active)**: Including `master-sync.md`, `test-automation.md`, and `update-docs.md`.

## Directory Structure
- `app.py`: The single-file Streamlit Hybrid Pipeline.
- `data/`: `assets/` (Godzilla/Yeti images) + Error Observability JSON logs.
- `tests/`: Automated Pytest verification suite (Contract testing, DuckDB testing).
- `.agents/`: Governance rules, product templates, agentic skills (including LLM-Council), and autonomous workflows.

## The Architecture of Decision
All major architecture decisions (including the pivot to Gamification) are permanently recorded in `.agents/architecture/adrs/`. We use the **LLM-Council** skill to run 5-agent peer-reviewed debates on all features before implementing code.

## Acknowledgments
Credit to the study `antigravity` repository for the base templates and agentic workflows.