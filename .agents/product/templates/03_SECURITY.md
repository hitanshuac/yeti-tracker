# Security & Access Spec

## 1. Data Governance & Storage Constraints
- **Strict Size Limit**: The repository must remain strictly under 10MB.
- **Enforcement**: All database files (`*.duckdb`, `*.db`) and Dead Letter Queue dumps (`*.parquet`) MUST be stored in the `data/` directory.
- The `data/` directory must be strictly ignored via `.gitignore` to prevent leaking data or violating size limits.

## 2. Secret Management
- **Environment Variables**: No secrets are currently required for the base Bronze ingestion layer. If APIs are integrated later, they must use `.env` files.
- **Agent Rules**: Never hallucinate or hardcode API keys or credentials in the source code.

## 3. Memory & Resource Safety
- DuckDB must be instantiated with strict PRAGMA limits (`memory_limit='2GB'`) to prevent Out-Of-Memory crashes in constrained environments.
