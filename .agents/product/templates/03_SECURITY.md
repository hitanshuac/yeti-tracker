# 03_SECURITY: Security & Governance

## 1. Threat Model & Data Privacy
Because Yeti-Tracker handles sensitive personal behavioral data (Diet, Transport, Location correlations), security through localization is paramount.

- **Local Execution ONLY**: The entire architecture (FastAPI + DuckDB) runs locally on the user's machine. Data never leaves the host.
- **Zero Third-Party APIs**: No external LLM or tracking API keys are required for the application to function.
- **File System Governance**: The dataset is strictly stored in `data/` and excluded from source control (via `.gitignore` except for the sample) to prevent accidental PII leakage.

## 2. Agentic Governance Constraints (Hack2Skill)
The Antigravity Brain (`.agents/`) enforces strict operational constraints:
- **Idempotency**: All workflows must be repeatable without side effects.
- **Storage Quota**: The repository must stay below 10MB. We ensure this by automatically purging `.pytest_cache`, `.ruff_cache`, and `__pycache__` before checkpoints.
- **Dependencies**: Only allow-listed dependencies from `requirements.txt` (FastAPI, DuckDB, Pandas) may be used. No heavy ML frameworks (TensorFlow, PyTorch) are permitted.

## 3. Input Validation
While ETL logic was minimized, FastAPI still protects the execution plane from malformed requests. However, since the EDA UI does not allow user input (it is a read-only analytics dashboard), injection attacks are naturally mitigated.
