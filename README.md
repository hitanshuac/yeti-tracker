# Yeti-Tracker: Carbon Footprint Tracking Assistant 🌍
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![DuckDB](https://img.shields.io/badge/duckdb-embedded-yellow.svg)

![Architecture Diagram](docs/assets/architecture_diagram_showcase.png)

## Overview
**Carbon Footprint Tracking**: A smart solution that helps individuals understand, track, and reduce their carbon footprint through simple actions and personalized insights.
We are building the backbone of the Yeti-Tracker using a minimalist, fault-tolerant Split-Plane Architecture centered around standard Python, Pydantic, and DuckDB.

## Dynamic Skill Integration
This repository leverages composable AI skills (`.agents/skills/`) to autonomously enforce SRE principles (e.g., DuckDB WAL, Memory Limits) and generate deterministic architecture diagrams using diagrams-as-code.

## Installation & Setup
```bash
git clone https://github.com/hitanshuac/yeti-tracker.git
cd yeti-tracker
python -m venv venv
venv\Scripts\activate
pip install pyarrow duckdb pydantic pytest ruff
```

## Current Capabilities
- **Rules**: Core Constraints (10MB Size Limit)
- **Python APIs**: `CarbonActivity` (Pydantic), PyArrow to DuckDB pipeline (`duckdb_ingest.py`), Parquet Dead Letter Queue (`processor.py`), Git Manager (`git_manager.py`).
- **Product Templates**: PRD, TAD, Security, Frontend, Tickets.
- **Skills**: Diagram Generator, DuckDB Optimizer, Pipeline Architect.
- **Workflows**: Generate Product Docs, Test Automation, Update Docs, Generate Diagrams, Publish Showcase, Semantic Release, Error Observability, Master Sync, Secure Checkpoint, Git Sync.

## Directory Structure
- `src/`: Python source code (models, ingestion pipelines, capabilities).
- `data/`: Git-ignored storage for `yeti.duckdb` and Parquet files.
- `.agents/`: Agentic workflows, skills, rules, and templates.
- `tests/`: Pytest automation suite.
- `docs/`: Product documents and diagram assets.

## Adoption Method
To inject this Agentic Brain into another project, copy the `.agents/` directory and configure your `git_manager.py` checkpoint workflows.

## Visual Reference Appendix
Technical structural diagram generated via D2/Python, styled via `generate_image`.

```mermaid
graph LR
    A[Client App] -->|Raw Carbon Data| B(PyArrow & Pydantic)
    B -->|Valid Data| C[(Local Embedded DB)]
    B -->|Invalid Data| D[(Parquet Quarantine)]
    
    style A fill:#0D1117,stroke:#00FFFF,stroke-width:2px,color:#fff
    style B fill:#0D1117,stroke:#A020F0,stroke-width:2px,color:#fff
    style C fill:#0D1117,stroke:#00FFFF,stroke-width:2px,color:#fff
    style D fill:#0D1117,stroke:#FF0000,stroke-width:2px,color:#fff
```

## Acknowledgments
Credit to the study antigravity repository for the agentic constraints framework.