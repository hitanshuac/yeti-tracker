# Frontend Specification

## 1. Core Mandate
Per our baseline architecture, the frontend UI is strictly **out of scope**. 

## 2. Interface
The Yeti-Tracker operates purely as a data engineering engine. The "interface" consists of:
- Terminal/CLI interactions.
- Agentic Workflows.
- Raw database queries via DuckDB.

## 3. Reason for Exclusion
The Hack2Skill constraints require the repository to be under 10MB. Building a production-grade React/Vite application introduces `node_modules` dependency risks and unnecessary bloat when the core judging criteria focus heavily on logical decision-making, efficiency, and clean code.
