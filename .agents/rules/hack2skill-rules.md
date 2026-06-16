# Hack2Skill Challenge Rules & Constraints

## 1. Structural Constraints
- **Repository Size**: Strictly less than 10 MB. All datasets, models, DuckDB files, and logs MUST be excluded via `.gitignore` (keep them in `data/`).
- **Branching**: Must use only a single branch (`main`). No feature branches or pull requests.
- **Repository State**: Must be public on GitHub.

## 2. Evaluation Focus Areas
- **Code Quality**: Clean, structured, readable, and maintainable code.
- **Security**: Safe and responsible implementation (e.g., no hardcoded secrets, using `.env`, validation).
- **Efficiency**: Optimal resource use (e.g., DuckDB PRAGMA limits, memory-safe streaming, avoiding heavy distributed orchestrators).
- **Testing**: Validation of functionality (e.g., Pytest, Pydantic validation DLQs).
- **Accessibility**: Inclusive and usable design (if applicable to UI).

## 3. Challenge Expectations & Submission
- Must demonstrate a smart, dynamic assistant with logical decision making.
- The `README.md` must clearly explain:
  - The chosen vertical
  - Approach and logic
  - How the solution works
  - Any assumptions made
