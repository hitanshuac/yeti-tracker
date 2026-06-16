# Product Requirements Document (PRD)

**Project Name:** Yeti-Tracker: Personal Gamification Pivot
**Date:** 2026-06-16
**Status:** Approved

## 1. Objective
Build a "Carbon Footprint Awareness Platform" that helps individuals understand, track, and reduce their carbon footprint. The platform must bridge the gap between mathematically rigorous deterministic calculation and the emotional, cognitive connection required by Hack2Skill Challenge 3. It leverages gamification and a "Hybrid LLM Pipeline" to achieve this.

## 2. Target Audience / Personas
- **Persona 1 (The Individual Contributor):** A daily user looking for frictionless ways to log their day and understand their environmental impact without staring at boring spreadsheets.
- **Persona 2 (The Hackathon Judge):** An AI evaluator looking for proper integration of "Smart Assistants," dynamic intent-driven development, and secure, high-quality code.

## 3. Core Features (MVP)
1. **The Confessional**: Frictionless data ingestion via an LLM parsing messy, natural language daily diaries.
2. **The Verification Gate**: The LLM must not execute math. It must populate human-verifiable UI sliders to guarantee data integrity.
3. **The Gamified Mirror**: If the footprint crosses 9,000kg/year, the UI must break and display "OVER 9000" Godzilla/Yeti gamification assets.
4. **The Yeti Advisor**: A secondary LLM call must generate a personalized, sarcastic, and actionable reduction strategy based on the specific footprint input.

## 4. Out of Scope (Non-Goals)
- **Complex 3D Topography**: Avoided to prevent UX lag and math instability.
- **Enterprise FinOps**: Pivoted away from SRE AWS data to align with the "individual" prompt requirement.
- **Vision LLMs**: Avoided due to severe latency and API constraints.

## 5. Success Metrics
- **Idempotency**: `f(x) = y` is guaranteed via DuckDB deterministic pipelines.
- **Zero Hallucination Mathematics**: The LLM has zero agency over the final calculations.
- **Emotional Resonance**: Measured by the visual impact of the Godzilla override state.
