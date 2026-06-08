# Core Hack2Skill Constraints

This rule enforces the critical constraints outlined in the Hack2Skill Challenge rules.

## 1. Repository Size Constraint
- **Rule**: The total repository size MUST be strictly under 10 MB.
- **Enforcement**: 
  - Ensure `.gitignore` is heavily utilized.
  - Exclude datasets, machine learning models, DuckDB databases (`*.duckdb`, `*.db`), and large logs.
  - Store all dynamic or generated data in a `data/` folder and ensure `data/` is ignored by Git.

## 2. Branching Constraint
- **Rule**: Only a single branch (`main`) is allowed.
- **Enforcement**: Do not create feature branches. Do not create pull requests. All commits must be made directly to the `main` branch.

## 3. Mandatory Output
- **Rule**: A comprehensive `README.md` is required.
- **Enforcement**: Must document the chosen vertical, approach/logic, operation instructions, and assumptions.

These rules must be respected by all autonomous tasks and workflows within this repository.
