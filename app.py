"""
Yeti-Tracker Application Module.

This module implements the Streamlit dashboard for the Yeti-Tracker Personal Carbon Footprint Tracker.
It integrates LLM parsing of natural language text into deterministic sliders,
and uses DuckDB to forecast yearly carbon footprint, gamifying the output with the "Over 9000" Godzilla trigger.
"""

import datetime
import json
import os
from pathlib import Path

import duckdb
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv(".secrets/.env")


# --- OBSERVABILITY & CONTRACTS ---
def log_error_to_json(error_type: str, component: str, message: str, log_file: str = "data/error_logs.json") -> None:
    """Logs errors to data/error_logs.json following the canonical schema."""
    if not error_type or not isinstance(error_type, str):
        raise ValueError(f"error_type must be a non-empty string, got: {error_type!r}")
    if not component or not isinstance(component, str):
        raise ValueError(f"component must be a non-empty string, got: {component!r}")
    if not message or not isinstance(message, str):
        raise ValueError(f"message must be a non-empty string, got: {message!r}")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    try:
        if os.path.exists(log_file):
            with open(log_file, encoding="utf-8") as f:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = []
        else:
            logs = []
    except Exception:
        logs = []

    before_count = len(logs)
    new_entry = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
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
        verified_logs = json.load(f)
        assert len(verified_logs) == before_count + 1, "Data loss detected during error logging."


class ParsedPersonalData(BaseModel):
    """Pydantic model representing parsed daily activities."""

    miles_driven: int
    ac_hours: int
    steaks_eaten: int


def sanitize_input(text: str) -> str:
    """Sanitizes raw input text to mitigate CWE-74 prompt injection."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    sanitized = text[:15000]
    for char in ["<", ">", "{", "}"]:
        sanitized = sanitized.replace(char, "")
    return sanitized.strip()


# --- STAGE 1: DUCKDB FORECASTING LEDGER ---
def run_duckdb_math(miles: int, ac_hours: int, steaks: int) -> tuple[float, int]:
    """Calculates the yearly forecasted carbon footprint and offset debt.

    Args:
        miles: Daily miles driven.
        ac_hours: Daily hours of AC usage.
        steaks: Number of beef meals eaten today.

    Returns:
        A tuple containing (yearly_co2_kg, trees_needed_to_offset).
    """
    conn = duckdb.connect()
    # Simple DuckDB math: (miles*0.4 + ac_hours*1.5 + steaks*7.0) * 365
    query = """
        SELECT
            ((? * 0.4) + (? * 1.5) + (? * 7.0)) * 365 as yearly_co2_kg
    """
    result = conn.execute(query, [miles, ac_hours, steaks]).fetchone()
    if not result:
        return 0.0, 0

    yearly_co2 = float(result[0])
    # A standard mature tree absorbs ~22kg of CO2 per year
    trees_needed = int(yearly_co2 / 22.0)

    return yearly_co2, trees_needed


# --- STAGE 2: THE LLM TRANSLATOR ---
def parse_messy_text(text: str) -> dict:
    """Uses LLM to extract JSON from messy natural language safely."""
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    default_payload = {"miles_driven": 20, "ac_hours": 5, "steaks_eaten": 0}

    if not api_key:
        st.error("Missing GROQ_API_KEY. Please set it in your environment.")
        log_error_to_json("EnvironmentError", "parse_messy_text", "Missing GROQ_API_KEY in environment variables.")
        return default_payload

    safe_text = sanitize_input(text)
    client = Groq(api_key=api_key)

    prompt = f"""
    Extract the daily activity details from the following messy text.
    We need exactly three integers:
    1. miles_driven (how many miles did they drive today?)
    2. ac_hours (how many hours was the AC or heating running?)
    3. steaks_eaten (how many beef meals did they eat?)

    Return ONLY a JSON object with this exact schema:
    {{
        "miles_driven": integer,
        "ac_hours": integer,
        "steaks_eaten": integer
    }}

    If any field is missing or cannot be parsed, use these defaults:
    miles_driven: 0, ac_hours: 0, steaks_eaten: 0.

    Messy Text: {safe_text}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
        )
        raw_json = json.loads(response.choices[0].message.content)
        validated = ParsedPersonalData(**raw_json)
        return validated.model_dump()

    except ValidationError as e:
        log_error_to_json(type(e).__name__, "parse_messy_text", str(e))
        st.error("LLM returned invalid schema. Falling back to defaults.")
        return default_payload
    except Exception as e:
        log_error_to_json(type(e).__name__, "parse_messy_text", str(e))
        st.error("LLM parsing failed. Falling back to defaults.")
        return default_payload


def get_yeti_advice(carbon: float, miles: int, ac: int, steaks: int, tier: str) -> str:
    """Uses LLM to generate a personalized, context-aware advice string based on the severity tier."""
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "I'm a Yeti without an API key, so I can't roast you. Just plant some trees, okay?"

    if tier == "Godzilla":
        system_msg = (
            "You are a terrified news anchor. A colossal Godzilla Kaiju just woke up "
            "because of the user's carbon footprint and is destroying the city! Scream at them in panic."
        )
    elif tier == "Yeti":
        system_msg = (
            "You are a furious Yeti. Your glaciers are melting into the ocean "
            "because of the user's carbon footprint. Roast them aggressively."
        )
    elif tier == "Vegeta":
        system_msg = (
            "You are an arrogant Saiyan prince. You just scanned their carbon footprint "
            "and it's over 5000. You are disgusted by their weak attempts at sustainability. Roast them."
        )
    else:
        system_msg = (
            "You are a slightly annoyed but polite environmental scientist. "
            "The user's footprint is okay, but could be better. Give them a snarky tip."
        )

    client = Groq(api_key=api_key)
    prompt = f"""
    {system_msg}
    The user's yearly carbon forecast is {carbon:,.0f} kg.
    Today, they drove {miles} miles, used the AC for {ac} hours, and ate {steaks} beef meals.

    Give them a 2-sentence roasting about their specific activities, and one actionable way to reduce their footprint.
    Be funny, dramatic, and slightly aggressive.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        log_error_to_json(type(e).__name__, "get_yeti_advice", str(e))
        return "My brain melted from the heat of your carbon footprint. Just stop eating so much beef, okay?"


def create_gauge_fig(
    value: float, title: str, max_val: float, color: str, prefix: str = "", suffix: str = ""
) -> go.Figure:
    """Creates a premium Plotly Gauge Indicator."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            title={"text": title, "font": {"color": "white"}},
            number={"prefix": prefix, "suffix": suffix, "font": {"color": color}},
            gauge={
                "axis": {"range": [0, max_val], "tickcolor": "white"},
                "bar": {"color": color},
                "bgcolor": "#1e1e1e",
                "borderwidth": 2,
                "bordercolor": "#333333",
                "steps": [
                    {"range": [0, max_val * 0.5], "color": "rgba(0,0,0,0)"},
                    {"range": [max_val * 0.5, max_val * 0.8], "color": "rgba(255,165,0,0.2)"},
                    {"range": [max_val * 0.8, max_val], "color": "rgba(255,0,0,0.3)"},
                ],
            },
        )
    )
    fig.update_layout(
        paper_bgcolor="#0e1117",
        font={"color": "white", "family": "Arial"},
        height=350,
        margin={"l": 20, "r": 20, "b": 20, "t": 50},
    )
    return fig


# --- STAGE 4: THE UI ---
if __name__ == "__main__":
    st.set_page_config(layout="wide", page_title="Yeti-Tracker Carbon Footprint")
    st.title("Yeti-Tracker: Know Your Footprint")

    if "parsed_data" not in st.session_state:
        st.session_state.parsed_data = {"miles_driven": 10, "ac_hours": 4, "steaks_eaten": 0}

    col1, col2 = st.columns([2, 1])

    with col2:
        st.markdown("### 1. The Confessional (LLM Auto-Fill)")
        messy_input = st.text_area(
            "Tell me about your day:",
            value=(
                "I drove about 40 miles round trip for work. Ate a huge steak for lunch. Left the AC on for 10 hours."
            ),
            height=100,
            help="Paste your natural language diary here. The AI will extract the parameters.",
        )

        if st.button("Extract Data", type="primary", help="Uses Groq to fill the sliders below."):
            with st.spinner("Translating..."):
                st.session_state.parsed_data = parse_messy_text(messy_input)

        st.markdown("---")
        st.markdown("### 2. Human Verification")
        st.info("The math engine ONLY uses these deterministic sliders. Verify the AI didn't hallucinate.")

        # Hybrid Sliders
        miles = st.slider("Miles Driven", 0, 500, st.session_state.parsed_data["miles_driven"])
        ac = st.slider("AC / Heating Hours", 0, 24, st.session_state.parsed_data["ac_hours"])
        steaks = st.slider("Beef Meals", 0, 5, st.session_state.parsed_data["steaks_eaten"])

        # Update session state manually if user slides
        st.session_state.parsed_data["miles_driven"] = miles
        st.session_state.parsed_data["ac_hours"] = ac
        st.session_state.parsed_data["steaks_eaten"] = steaks

        st.markdown("---")
        calculate_clicked = st.button("Calculate Impact", type="primary", use_container_width=True)

    with col1:
        if calculate_clicked:
            carbon, trees = run_duckdb_math(miles, ac, steaks)

            # THE 3-TIER GAMIFICATION TRIGGER
            if carbon > 15000:
                tier = "Godzilla"
                st.error("🚨 APOCALYPTIC WARNING 🚨")
                st.markdown(
                    f"<h1 style='text-align: center; color: red; font-size: 60px;'>"
                    f"TOTAL EXTINCTION ({carbon:,.0f} kg)</h1>",
                    unsafe_allow_html=True,
                )
                img_path = Path("data/assets/godzilla_extinction.png")
            elif carbon > 9000:
                tier = "Yeti"
                st.error("🚨 CRITICAL WARNING 🚨")
                st.markdown(
                    f"<h1 style='text-align: center; color: red; font-size: 60px;'>"
                    f"THE ICE IS GONE ({carbon:,.0f} kg)</h1>",
                    unsafe_allow_html=True,
                )
                img_path = Path("data/assets/yeti_awakening.png")
            elif carbon > 5000:
                tier = "Vegeta"
                st.warning("⚠️ WARNING: IT'S OVER 5000!")
                st.markdown(
                    f"<h3 style='text-align: center;'>Yearly Forecast: {carbon:,.0f} kg</h3>", unsafe_allow_html=True
                )
                img_path = Path("data/assets/vegeta_scouter.png")
            else:
                tier = "Normal"
                img_path = None

            if img_path:
                if img_path.exists():
                    st.image(str(img_path), use_container_width=True)
                else:
                    st.warning(f"Image asset missing from {img_path}")
            else:
                st.success("✅ Sustainable Human Footprint")
                st.markdown("### Live 365-Day Forecasting Telemetry")
                col_graph1, col_graph2 = st.columns(2)

                with col_graph1:
                    fig_carbon = create_gauge_fig(
                        value=carbon, title="Yearly Forecasted Carbon", max_val=15000, color="#00ffaa", suffix=" kg"
                    )
                    st.plotly_chart(fig_carbon, use_container_width=True)

                with col_graph2:
                    fig_trees = create_gauge_fig(
                        value=trees, title="Trees Needed to Offset", max_val=700, color="#ff0055", suffix=" trees"
                    )
                    st.plotly_chart(fig_trees, use_container_width=True)

            # YETI ADVISOR (Dynamic Assistant) - Auto Runs seamlessly!
            st.markdown("---")
            st.markdown("### 🎙️ The Smart Advisor")
            with st.spinner("Analyzing your doom..."):
                advice = get_yeti_advice(carbon, miles, ac, steaks, tier)
                st.info(advice)
        else:
            st.info(
                "👈 Adjust your daily inputs and click **'Calculate Impact'** "
                "to view your 365-day cinematic forecast."
            )
