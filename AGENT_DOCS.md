# Yeti-Tracker: Carbon Footprint Tracking Gamification 🌍

## The Chosen Vertical
**Carbon Footprint Tracking**: A smart solution that helps individuals understand, track, and reduce their carbon footprint through simple actions, gamification, and personalized insights (Hack2Skill Challenge 3).

## Approach and Logic
We solved the core problem of AI "Prompt Wars" by bridging the gap between non-deterministic LLMs and strict deterministic mathematics. We implemented the **Hybrid LLM Pipeline**:
1. **Frictionless Ingestion**: We use an LLM (`llama-3.1-8b-instant`) to parse natural language diary entries into structured data, eliminating complex web forms.
2. **Idempotency Gate**: The LLM *only* populates Streamlit UI sliders. This places a Human-in-the-Loop before any math executes, guaranteeing 100% data integrity and eliminating hallucination drift.
3. **DuckDB Forecasting**: The deterministic core calculates the 365-day cumulative footprint from the seed sliders.

## Gamification and Emotional Connection
To comply with the SME's requirement for "emotional awareness", we avoid dry, boring dashboards.
- If the footprint is sustainable, the UI remains a hyper-professional enterprise dashboard.
- If the footprint crosses 9,000kg, the UI violently shatters into an "OVER 9000" Godzilla meme, shocking the user.
- **The Yeti Advisor**: A secondary LLM dynamically roasts the user based on their specific inputs (e.g., driving 400 miles) and provides one actionable tip to reduce their footprint, satisfying the "Smart Assistant" and "Reduction" requirements.

## How the Solution Works
1. **The Confessional**: User pastes unstructured text describing their day.
2. **LLM Extraction**: Groq parses the text into Miles, AC Hours, and Beef Meals.
3. **Verification**: User approves the UI sliders.
4. **Execution**: DuckDB compounds the math over a year.
5. **Visualization**: Streamlit renders either green sustainable gauges or the shattering Godzilla alert.
6. **Advice**: The user clicks "Ask the Yeti" to trigger a personalized LLM reduction strategy.

## Assumptions Made
- Gamification and meme culture ("It's Over 9000") is a highly effective psychological tool for creating cognitive dissonance and emotional awareness regarding carbon footprints, far more effective than static spreadsheets.
- Storage size is constrained strictly to under 10MB on GitHub.
- Users want the frictionless ease of an AI chat, but the mathematical certainty of an Excel spreadsheet.

---
*Credits to the original "study antigravity repo" for the base environment and agentic governance framework.*
