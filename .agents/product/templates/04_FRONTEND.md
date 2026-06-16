# Frontend Architecture & Design

## 1. UX/UI Principles
- **Framework**: Streamlit is used to rapidly construct the UI and bind state natively to Python execution without React/Node boilerplate.
- **Color Palette**: Dark mode by default (`#0e1117`).
- **Gamified Metaphors**: Visceral impact is prioritized over dry statistics. The UI visually degrades when absurd footprint thresholds are crossed.

## 2. Layout Structure
A 2-column layout (`col1`, `col2` with a 2:1 ratio) to separate the Data Ingestion (Right) from the Data Visualization (Left).

### Right Column: The Ingestion & Verification
1. **The Confessional**: A `st.text_area` for natural language input. A primary button ("Extract Data") triggers the LLM.
2. **Human Verification Sliders**: Three standard `st.slider` components mapped to Streamlit Session State (`st.session_state.parsed_data`). The math engine listens to these, not the LLM.

### Left Column: The Dashboard / Gamification
1. **State 1 (Normal)**: Displays two `create_gauge_fig` Plotly dials showing Yearly Carbon (green) and Tree Offset Debt (red).
2. **State 2 (Yeti Alert)**: Triggers at > 5,000kg. Hides gauges, displays `data/assets/yeti_alert.png` and a warning.
3. **State 3 (Godzilla Alert)**: Triggers at > 9,000kg. Displays `data/assets/godzilla_over_9000.png` and a massive red HTML header ("IT'S OVER 9000!!!").
4. **The Yeti Advisor**: A secondary button at the bottom of the left column triggering the LLM roasting function `get_yeti_advice`.
