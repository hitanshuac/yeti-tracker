import json
import os
import textwrap

import duckdb
import plotly.graph_objects as go
import streamlit as st
from pydantic import BaseModel


def log_error_to_json(error_type: str, component: str, message: str, log_file: str = "data/error_logs.json"):
    """Appends an error entry to a JSON file idempotently, ensuring schema compliance."""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    if not os.path.exists(log_file):
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump([], f)

    with open(log_file, encoding="utf-8") as f:
        try:
            logs = json.load(f)
            if not isinstance(logs, list):
                logs = []
        except json.JSONDecodeError:
            logs = []

    before_count = len(logs)
    new_entry = {
        "error_type": error_type,
        "component": component,
        "message": message,
        "status": "UNRESOLVED",
        "resolution_strategy": None,
    }
    logs.append(new_entry)

    temp_file = f"{log_file}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    os.replace(temp_file, log_file)

    with open(log_file, encoding="utf-8") as f:
        verified = json.load(f)
        assert len(verified) == before_count + 1, "Data loss detected during logging"


class ParsedPersonalData(BaseModel):
    """Pydantic model representing parsed activities."""

    miles_driven: int
    flight_miles: int
    transit_miles: int
    ac_hours: int
    restaurant_meals: int


def sanitize_input(text: str) -> str:
    """Sanitizes raw input text to mitigate CWE-74 prompt injection."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    sanitized = text[:15000]
    for char in ["<", ">", "{", "}"]:
        sanitized = sanitized.replace(char, "")
    return sanitized.strip()


def run_duckdb_math(
    car_miles: int,
    flight_miles: int,
    transit_miles: int,
    ac_hours: int,
    restaurant_meals: int,
    dataset_path: str = "data/carbon_factors.csv",
    mode: str = "Daily Confessional",
) -> tuple[float, float, dict]:
    """Calculates forecasted carbon footprint and financial cost using DuckDB."""
    conn = duckdb.connect()

    try:
        query = f"SELECT activity, co2_kg_per_unit, social_cost_usd_per_kg FROM read_csv_auto('{dataset_path}')"
        results = conn.execute(query).fetchall()
        factors = {row[0]: {"co2": float(row[1]), "scc": float(row[2])} for row in results}
    except Exception as e:
        log_error_to_json(type(e).__name__, "run_duckdb_math", str(e))
        factors = {}

    def get_factor(activity: str, key: str, default: float) -> float:
        return factors.get(activity, {}).get(key, default)

    daily_car_co2 = car_miles * get_factor("miles_driven", "co2", 0.4)
    daily_flight_co2 = flight_miles * get_factor("flight_miles", "co2", 0.25)
    daily_transit_co2 = transit_miles * get_factor("transit_miles", "co2", 0.14)
    daily_ac_co2 = ac_hours * get_factor("ac_hours", "co2", 1.5)
    daily_restaurant_co2 = restaurant_meals * get_factor("restaurant_meal", "co2", 8.5)

    if mode == "Daily Confessional":
        yearly_miles = (daily_car_co2 + daily_flight_co2 + daily_transit_co2) * 365
        yearly_ac = daily_ac_co2 * 365
        yearly_restaurant = daily_restaurant_co2 * 365
    else:
        yearly_miles = daily_car_co2 + daily_flight_co2 + daily_transit_co2
        yearly_ac = daily_ac_co2
        yearly_restaurant = daily_restaurant_co2

    yearly_co2 = yearly_miles + yearly_ac + yearly_restaurant

    carbon_tax_usd = (
        yearly_miles * get_factor("miles_driven", "scc", 0.19)
        + yearly_ac * get_factor("ac_hours", "scc", 0.19)
        + yearly_restaurant * get_factor("restaurant_meal", "scc", 2.50)
    )

    breakdown = {"Transportation": yearly_miles, "AC/Heating": yearly_ac, "Eating Out": yearly_restaurant}

    return yearly_co2, carbon_tax_usd, breakdown


def parse_messy_text(text: str, mode: str = "Daily Confessional") -> dict:
    """Uses LLM to extract JSON from messy natural language safely."""
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    default_payload = {"miles_driven": 20, "flight_miles": 0, "transit_miles": 0, "ac_hours": 5, "restaurant_meals": 0}

    if not api_key:
        st.error("Missing GROQ_API_KEY. Please set it in your environment.")
        log_error_to_json("EnvironmentError", "parse_messy_text", "Missing GROQ_API_KEY.")
        return default_payload

    safe_text = sanitize_input(text)
    client = Groq(api_key=api_key)

    if mode == "Daily Confessional":
        instructions = "1. miles_driven\\n2. flight_miles\\n3. transit_miles\\n4. ac_hours\\n5. restaurant_meals"
    else:
        instructions = "1. miles_driven (YEARLY)\\n2. flight_miles (YEARLY)\\n3. transit_miles (YEARLY)\\n4. ac_hours (YEARLY)\\n5. restaurant_meals (YEARLY)"  # noqa: E501

    prompt = f"Extract exactly five integers based on their {mode} input: {instructions}. Estimate distances in miles. Output valid JSON. Text: {safe_text}"  # noqa: E501

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        data = json.loads(content)
        return data
    except Exception as e:
        log_error_to_json(type(e).__name__, "parse_messy_text", str(e))
        return default_payload


def fetch_rag_context(text: str, dataset_path: str = "data/carbon_factors.csv") -> str:
    """Uses DuckDB to extract context from the dataset."""
    import re

    conn = duckdb.connect()
    try:
        words = re.findall(r"\w+", text.lower())
        keywords = [w for w in words if len(w) > 4]
        if not keywords:
            return ""

        conditions = [f"LOWER(description) LIKE '%{kw}%' OR LOWER(activity) LIKE '%{kw}%'" for kw in keywords]
        where_clause = " OR ".join(conditions)

        query = f"SELECT activity, description, co2_kg_per_unit, social_cost_usd_per_kg FROM read_csv_auto('{dataset_path}') WHERE {where_clause} LIMIT 3"  # noqa: E501
        results = conn.execute(query).fetchall()

        if not results:
            return ""

        context_lines = ["RAG CONTEXT (Carbon Factors from Database):"]
        for row in results:
            context_lines.append(f"- {row[0]} ({row[1]}): {row[2]} kg CO2/unit, ${row[3]} SCC/unit")
        return "\n".join(context_lines)
    except Exception as e:
        log_error_to_json(type(e).__name__, "fetch_rag_context", str(e))
        return ""


def get_yeti_advice(
    carbon: float,
    tax: float,
    car_miles: int,
    flight_miles: int,
    transit_miles: int,
    ac: int,
    restaurant_meals: int,
    tier: str,
    goal: str,
    rag_context: str = "",
    mode: str = "Daily Confessional",
) -> str:
    """Uses LLM to generate advice."""
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "I am offline. Please provide an API key."

    if tier == "Godzilla":
        system_msg = (
            "You are an aggressive, witty, and dramatic environmental enforcer. The user is destroying the planet."
        )
    elif tier == "Yeti":
        system_msg = "You are a tough-love climate coach. The user needs to step up their game."
    else:
        system_msg = "You are a friendly environmental scientist. The user's footprint is okay, but could be better."

    if mode == "Daily Confessional":
        extra_txt = f"The user's 365-DAY YEARLY FORECAST is {carbon:,.0f} kg, creating a Social Cost of Carbon (Tax Debt) of ${tax:,.2f} USD. (Note: This assumes they repeat today's actions every day for a year).\\nToday, they traveled {car_miles} miles by car, {flight_miles} miles by plane, and {transit_miles} miles by train/bus.\\nThey used the AC for {ac} hours, and ate out at restaurants {restaurant_meals} times."  # noqa: E501
    else:
        extra_txt = f"The user's EXACT YEARLY FORECAST is {carbon:,.0f} kg, creating a Social Cost of Carbon (Tax Debt) of ${tax:,.2f} USD.\\nThis year, they will travel {car_miles} miles by car, {flight_miles} miles by plane, and {transit_miles} miles by train/bus.\\nThey will use the AC for {ac} hours, and eat out at restaurants {restaurant_meals} times."  # noqa: E501

    prompt = textwrap.dedent(f"""
        {system_msg}
        The user's primary goal today is: {goal}. YOU MUST TAILOR YOUR ADVICE SPECIFICALLY TO THIS GOAL.
        {extra_txt}
        {rag_context}
        Give them EXACTLY 2 SENTENCES of advice about their specific activities.
        Sentence 1: A witty observation connecting their actions to their massive yearly forecast.
        Sentence 2: One actionable way to reduce their footprint that ALIGNS PERFECTLY with their stated primary goal.
        CRITICAL INSTRUCTION: Do not generate contradictory nonsense.
        CRITICAL INSTRUCTION: DO NOT be mean or insulting. Emphasize realistic optimization.
        CRITICAL INSTRUCTION: You must output exactly ONE paragraph containing exactly TWO sentences.
    """)

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        log_error_to_json(type(e).__name__, "get_yeti_advice", str(e))
        return ""


def create_gauge_chart(value: float, max_value: float, title: str) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title, "font": {"color": "white"}},
            gauge={
                "axis": {"range": [None, max_value], "tickcolor": "white"},
                "bar": {"color": "#ff4b4b"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "gray",
                "steps": [
                    {"range": [0, max_value * 0.3], "color": "lightgreen"},
                    {"range": [max_value * 0.3, max_value * 0.7], "color": "yellow"},
                    {"range": [max_value * 0.7, max_value], "color": "salmon"},
                ],
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="#0e1117",
        font={"color": "white", "family": "Arial"},
        height=250,
        margin={"l": 20, "r": 20, "b": 20, "t": 50},
    )
    return fig


def create_breakdown_bar_chart(breakdown: dict) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Bar(
                x=list(breakdown.keys()),
                y=list(breakdown.values()),
                marker_color=["#1f77b4", "#ff7f0e", "#2ca02c"],
            )
        ]
    )
    fig.update_layout(
        title={"text": "CO2 Source Breakdown (kg)", "font": {"color": "white"}},
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font={"color": "white", "family": "Arial"},
        height=350,
        margin={"l": 20, "r": 20, "b": 20, "t": 50},
    )
    fig.update_yaxes(gridcolor="#333333")
    return fig


if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Yeti-Tracker Carbon Footprint")
    st.title("Yeti-Tracker: Know Your Footprint")

    default_vals = {"car_miles": 10, "flight_miles": 0, "transit_miles": 0, "ac_hours": 4, "restaurant_meals": 0}
    for k, v in default_vals.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "last_extracted_text" not in st.session_state:
        st.session_state.last_extracted_text = "I drove about 40 miles round trip for work. Ate out at a fancy restaurant for lunch. Left the AC on for 10 hours."  # noqa: E501

    def handle_extract():
        messy = st.session_state.get("confessional_input", "")
        mode = st.session_state.get("input_mode_select", "Daily Confessional")
        st.session_state.last_extracted_text = messy
        parsed = parse_messy_text(messy, mode)
        st.session_state.car_miles = parsed.get("miles_driven", 0)
        st.session_state.flight_miles = parsed.get("flight_miles", 0)
        st.session_state.transit_miles = parsed.get("transit_miles", 0)
        st.session_state.ac_hours = parsed.get("ac_hours", 0)
        st.session_state.restaurant_meals = parsed.get("restaurant_meals", 0)

    def handle_calculate():
        messy = st.session_state.get("confessional_input", "")
        last = st.session_state.get("last_extracted_text", "")
        if messy != last:
            handle_extract()
            st.session_state.auto_extracted = True
        st.session_state.run_math = True

    col1, col2 = st.columns([2, 1])

    with col2:
        st.markdown("### 1. The Confessional (LLM Auto-Fill)")

        input_mode = st.selectbox(
            "Select Input Mode",
            ["Daily Confessional", "Yearly Lifestyle Forecaster"],
            key="input_mode_select",
            help="Toggle mode.",
        )

        if input_mode == "Daily Confessional":
            prompt_text = "Tell me about your day (Click Extract Data first!):"
            default_text = "I drove about 40 miles round trip for work. Ate out at a fancy restaurant for lunch. Left the AC on for 10 hours."  # noqa: E501
        else:
            prompt_text = "Describe your typical year (Click Extract Data first!):"
            default_text = (
                "I fly cross-country twice a year, drive about 10,000 miles for work, and eat out every weekend."
            )

        messy_input = st.text_area(
            prompt_text,
            value=default_text,
            height=100,
            key="confessional_input",
        )

        st.button("Extract Data", type="primary", on_click=handle_extract, help="Auto-fill inputs.")

        st.markdown("---")
        st.markdown("### 2. Human Verification & Goals")

        optimization_goal = st.selectbox(
            "What is your primary goal today?", ["Save Money", "Save Time", "Maximize Comfort", "Save the Planet"]
        )

        st.info("The math engine ONLY uses these deterministic sliders. Verify the AI didn't hallucinate.")

        if input_mode == "Daily Confessional":
            c_max, f_max, t_max, a_max, r_max = 1000, 5000, 1000, 24, 10
        else:
            c_max, f_max, t_max, a_max, r_max = 50000, 100000, 50000, 8760, 1095

        cm = st.session_state.car_miles
        st.slider("Car Miles Driven", 0, max(c_max, cm), key="car_miles")

        fm = st.session_state.flight_miles
        st.slider("Flight Miles", 0, max(f_max, fm), key="flight_miles")

        tm = st.session_state.transit_miles
        st.slider("Public Transit Miles", 0, max(t_max, tm), key="transit_miles")

        ach = st.session_state.ac_hours
        st.slider("AC / Heating Hours", 0, max(a_max, ach), key="ac_hours")

        rm = st.session_state.restaurant_meals
        st.slider("Restaurant Meals (Eating Out)", 0, max(r_max, rm), key="restaurant_meals")

        st.markdown("---")
        st.button("Calculate Financial Impact", type="primary", use_container_width=True, on_click=handle_calculate)

    with col1:
        if st.session_state.get("run_math", False):
            st.session_state.run_math = False

            if st.session_state.pop("auto_extracted", False):
                st.success("✅ Auto-extracted your new text!")

            c_miles = st.session_state.car_miles
            f_miles = st.session_state.flight_miles
            t_miles = st.session_state.transit_miles
            a_hours = st.session_state.ac_hours
            r_meals = st.session_state.restaurant_meals

            carbon, tax_usd, breakdown = run_duckdb_math(c_miles, f_miles, t_miles, a_hours, r_meals, mode=input_mode)

            if carbon > 30000:
                tier = "Godzilla"
                color = "#ff4b4b"
                msg = f"TOTAL EXTINCTION ({carbon:,.0f} kg)"
                img_path = "data/assets/godzilla.jpg"
            elif carbon > 15000:
                tier = "Yeti"
                color = "#ffaa00"
                msg = f"AVALANCHE WARNING ({carbon:,.0f} kg)"
                img_path = "data/assets/yeti.jpg"
            elif carbon > 9000:
                tier = "Vegeta"
                color = "#ffd700"
                msg = f"OVER 9000! ({carbon:,.0f} kg)"
                img_path = "data/assets/vegeta.jpg"
            else:
                tier = "Human"
                color = "#00cc66"
                msg = f"ACCEPTABLE IMPACT ({carbon:,.0f} kg)"
                img_path = None

            st.markdown(f"<h1 style='color: {color}; font-size: 3em;'>{msg}</h1>", unsafe_allow_html=True)

            if img_path and os.path.exists(img_path):
                st.image(img_path, width=400)

            st.markdown("---")
            st.markdown("### 🎙️ The Smart Advisor")
            with st.spinner("Analyzing your financial doom..."):
                rag_context = fetch_rag_context(messy_input)
                advice = get_yeti_advice(
                    carbon,
                    tax_usd,
                    c_miles,
                    f_miles,
                    t_miles,
                    a_hours,
                    r_meals,
                    tier,
                    optimization_goal,
                    rag_context,
                    mode=input_mode,
                )
                safe_advice = advice.replace("$", r"\$")
                st.info(safe_advice)

            st.markdown("---")

            mc1, mc2 = st.columns(2)
            with mc1:
                st.markdown("### Carbon Tax Ledger")
                fig_tax = create_gauge_chart(tax_usd, 5000, "Social Cost of Carbon (USD)")
                st.plotly_chart(fig_tax, use_container_width=True)

            with mc2:
                st.markdown("### CO2 Source Breakdown")
                fig_breakdown = create_breakdown_bar_chart(breakdown)
                st.plotly_chart(fig_breakdown, use_container_width=True)
