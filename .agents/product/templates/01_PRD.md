# Product Requirements Document (PRD)

**Project Name:** Yeti-Tracker: Indian Carbon Gamification Pivot
**Date:** 2026-06-18
**Status:** Approved

## 1. Objective
Build an "Indian Carbon Footprint Advisory Engine" that helps individuals understand, track, and reduce their carbon footprint. The platform bridges the gap between mathematically rigorous deterministic calculation (Social Cost of Carbon in INR) and emotional, cognitive connection required by Hack2Skill Challenge 3. It leverages gamification and a "Hybrid LLM Pipeline" to achieve this.

## 2. Target Audience / Personas
- **Persona 1 (The Indian Commuter):** A daily user looking for frictionless ways to log their day (e.g., Metro rides in Mumbai, AC usage during summer) and understand their financial and environmental impact.
- **Persona 2 (The Hackathon Judge):** An AI evaluator looking for proper integration of "Smart Assistants," dynamic intent-driven development, deterministic state tracking, and secure, high-quality code.

## 3. Core Features (MVP)
1. **The Continuous Confessional**: Frictionless data ingestion via an LLM parsing messy, natural language daily diaries, utilizing a recursive UI loop that tracks history per-session.
2. **The Verification Gate**: The LLM must populate human-verifiable UI sliders (strictly using Kilometers and Hours) to guarantee data integrity and bypass LLM math hallucinations.
3. **The INR Gamified Mirror**: A deterministic DuckDB engine calculates the exact Social Cost of Carbon at ₹15.80/kg. High-footprint users trigger "Catastrophe Tiers" with aggressive visual and textual roasting.
4. **The Smart Yeti Advisor**: A secondary LLM call dynamically generates a personalized, context-aware reduction strategy (Maximum Impact vs. Convenience) guaranteeing at least a 20% footprint reduction without redundant advice.

## 4. Out of Scope (Non-Goals)
- **Complex 3D Topography**: Avoided to prevent UX lag and math instability.
- **Enterprise FinOps**: Pivoted away from SRE AWS data to align with the "individual" prompt requirement.
- **Vision LLMs**: Avoided due to severe latency and API constraints.

## 5. Success Metrics
- **Idempotency**: `f(x) = y` is guaranteed via DuckDB deterministic pipelines.
- **Zero Hallucination Mathematics**: The LLM has zero agency over the final calculations; math expressions are intercepted and computed strictly by the engine.
- **Emotional Resonance**: Measured by the visual impact of the Catastrophe tier override states and aggressive INR tax metrics.
