# pylint: disable=line-too-long,broad-exception-caught
"""
Yeti-Tracker: Personal Carbon Footprint Gamification Dashboard.

This file is a **thin UI orchestrator**  it defines the Streamlit layout,
widgets, and callbacks but delegates all business logic to the ``src/`` modules.
"""

import random

import streamlit as st

from src.carbon_engine import classify_tier, run_duckdb_math
from src.history import (
    append_history,
)
from src.llm import AdvisorRequest, get_advisor_response, parse_confession
from src.security import sanitize_input
from src.state_manager import init_state
from src.ui.components import (
    _render_asset_image,
    _render_calculation_expander,
    _render_confessional,
    _render_history_section,
    _render_sliders,
    _render_top_progress_bars,
)
from src.ui.dashboard import (
    _render_bottom_advisor_dashboard,
    _render_financial_dashboard,
)

# ---------------------------------------------------------------------------
# Callbacks (thin wrappers that update session_state)
# ---------------------------------------------------------------------------


def _handle_extract() -> bool:
    """Parse the confessional text and populate slider values."""
    messy = sanitize_input(st.session_state.get("confessional_input", ""))
    st.session_state.last_extracted_text = messy
    parsed = parse_confession(messy)

    if not parsed.is_valid:
        st.error(parsed.rejection_reason)
        return False

    st.session_state.car_km = getattr(parsed, "car_km", 0)
    st.session_state.two_wheeler_km = getattr(parsed, "two_wheeler_km", 0)
    st.session_state.auto_rickshaw_km = getattr(parsed, "auto_rickshaw_km", 0)
    st.session_state.flight_km = getattr(parsed, "flight_km", 0)
    st.session_state.bus_km = getattr(parsed, "bus_km", 0)
    st.session_state.train_metro_km = getattr(parsed, "train_metro_km", 0)
    st.session_state.ac_hours = getattr(parsed, "ac_hours", 0)
    st.session_state.restaurant_meals = getattr(parsed, "restaurant_meals", 0)
    st.session_state.untracked_activities = getattr(parsed, "untracked_activities", [])

    # Save AI baselines for SRE Override tracking
    st.session_state.ai_car_km = st.session_state.car_km
    st.session_state.ai_two_wheeler_km = st.session_state.two_wheeler_km
    st.session_state.ai_auto_rickshaw_km = st.session_state.auto_rickshaw_km
    st.session_state.ai_flight_km = st.session_state.flight_km
    st.session_state.ai_bus_km = st.session_state.bus_km
    st.session_state.ai_train_metro_km = st.session_state.train_metro_km
    st.session_state.ai_ac_hours = st.session_state.ac_hours
    st.session_state.ai_restaurant_meals = st.session_state.restaurant_meals

    st.session_state.is_extracting = True
    st.session_state.show_missing_electricity_prompt = True
    return True


def _handle_reply() -> None:
    """Append the user's reply to confessional and re-extract."""
    reply = st.session_state.get("reply_input", "")
    if reply:
        st.session_state.confessional_input += f"\n\nYeti Advisor Response: {reply}"
        st.session_state.reply_input = ""
        if _handle_extract():
            st.session_state.auto_extracted = True
        st.session_state.run_math = True
        st.session_state.has_calculated = True


def _handle_calculate() -> None:
    """Trigger the calculation pipeline."""
    messy = sanitize_input(st.session_state.get("confessional_input", ""))
    last = st.session_state.get("last_extracted_text", "")
    if messy != last:
        if _handle_extract():
            st.session_state.auto_extracted = True

    # Detect SRE Human Override
    override_fields = [
        ("car_km", "ai_car_km", 0),
        ("two_wheeler_km", "ai_two_wheeler_km", 0),
        ("auto_rickshaw_km", "ai_auto_rickshaw_km", 0),
        ("flight_km", "ai_flight_km", 0),
        ("bus_km", "ai_bus_km", 0),
        ("train_metro_km", "ai_train_metro_km", 0),
        ("ac_hours", "ai_ac_hours", 0),
        ("restaurant_meals", "ai_restaurant_meals", 0),
    ]
    override = any(
        st.session_state.get(field) != st.session_state.get(ai_field, default)
        for field, ai_field, default in override_fields
    )

    st.session_state.human_override = override
    st.session_state.run_math = True
    st.session_state.has_calculated = True
    st.session_state.show_missing_electricity_prompt = False


def _handle_slider_change() -> None:
    """Reset calculation state on slider movement to prevent API spam."""
    st.session_state.has_calculated = False
    st.session_state.run_math = False


def _set_random_persona() -> None:
    """Set a random demo persona with hardcoded values  zero LLM calls."""
    personas = [
        {
            "name": "The Commuter",
            "text": (
                "The Commuter: I drive about 30 km to the office in Andheri every weekday. "
                "No flights. Eat out once a week at a local restaurant."
            ),
            "car_km": 7800,
            "two_wheeler_km": 0,
            "auto_rickshaw_km": 0,
            "flight_km": 0,
            "bus_km": 0,
            "train_metro_km": 0,
            "ac_hours": 0,
            "restaurant_meals": 52,
        },
        {
            "name": "The Crypto Bro",
            "text": (
                "The Crypto Bro: I run 5 AC units 24/7 for my mining rig in Pune. "
                "I eat out 3 times a day. I fly business class to Goa once a month."
            ),
            "car_km": 0,
            "two_wheeler_km": 0,
            "auto_rickshaw_km": 0,
            "flight_km": 9600,
            "bus_km": 0,
            "train_metro_km": 0,
            "ac_hours": 120,
            "restaurant_meals": 1095,
        },
        {
            "name": "The Corporate Jetsetter",
            "text": (
                "The Corporate Jetsetter: I fly Delhi-Bangalore every week for work. "
                "I take Ola everywhere (maybe 80 km a week). Eat out every day."
            ),
            "car_km": 4160,
            "two_wheeler_km": 0,
            "auto_rickshaw_km": 0,
            "flight_km": 145600,
            "bus_km": 0,
            "train_metro_km": 0,
            "ac_hours": 0,
            "restaurant_meals": 365,
        },
        {
            "name": "The Eco-Warrior",
            "text": (
                "The Eco-Warrior: I ride my bike to work. No AC. Eat out maybe once a month. No flights."
            ),
            "car_km": 0,
            "two_wheeler_km": 2600,
            "auto_rickshaw_km": 0,
            "flight_km": 0,
            "bus_km": 0,
            "train_metro_km": 2600,
            "ac_hours": 0,
            "restaurant_meals": 12,
        },
        {
            "name": "The Suburbanite",
            "text": (
                "The Suburbanite: I drive an SUV about 60 km a day in Noida for errands. "
                "Keep the AC blasted all summer. Fly to Kerala once a year for vacation."
            ),
            "car_km": 21900,
            "two_wheeler_km": 0,
            "auto_rickshaw_km": 0,
            "flight_km": 2400,
            "bus_km": 0,
            "train_metro_km": 0,
            "ac_hours": 16,
            "restaurant_meals": 104,
        },
        {
            "name": "The Last-Mile Addict",
            "text": (
                "The Last-Mile Addict: I order groceries from Zepto 3 times a day "
                "and buy fast fashion on Myntra weekly. "
                "I also take auto-rickshaws for about 5km every day to the metro station."
            ),
            "car_km": 0,
            "two_wheeler_km": 0,
            "auto_rickshaw_km": 1825,
            "flight_km": 0,
            "bus_km": 0,
            "train_metro_km": 1825,
            "ac_hours": 0,
            "restaurant_meals": 0,
            "untracked_activities": [
                "Zepto grocery deliveries 3x daily",
                "Myntra fast fashion weekly",
            ],
        },
        {
            "name": "The Home Chef",
            "text": (
                "The Home Chef: I cook all my meals at home using an LPG cylinder and barely travel. "
                "I run the AC for about 4 hours every afternoon."
            ),
            "car_km": 0,
            "two_wheeler_km": 0,
            "auto_rickshaw_km": 0,
            "flight_km": 0,
            "bus_km": 0,
            "train_metro_km": 0,
            "ac_hours": 4,
            "restaurant_meals": 0,
            "untracked_activities": ["LPG cylinder for daily cooking"],
        },
    ]
    persona = random.choice(personas)
    st.session_state.confessional_input = persona["text"]
    st.session_state.last_extracted_text = persona["text"]
    for key in [
        "car_km",
        "two_wheeler_km",
        "auto_rickshaw_km",
        "flight_km",
        "bus_km",
        "train_metro_km",
        "ac_hours",
        "restaurant_meals",
    ]:
        st.session_state[key] = persona[key]

    st.session_state["untracked_activities"] = persona.get("untracked_activities", [])
    # Auto-trigger calculation  no LLM needed
    st.session_state.run_math = True
    st.session_state.has_calculated = True
    st.session_state.show_missing_electricity_prompt = False


def _toggle_rescue() -> None:
    """Toggle between doom and rescue chart views."""
    current = st.session_state.get("show_rescue", False)
    st.session_state.show_rescue = not current


# ---------------------------------------------------------------------------
# UI Sections
# ---------------------------------------------------------------------------


def _cached_advisor_call(req_json: str) -> str:
    """Memoize LLM calls to prevent thread blocking."""
    req = AdvisorRequest.model_validate_json(req_json)
    return get_advisor_response(req).model_dump_json()


def _handle_math_success() -> None:
    if st.session_state.pop("auto_extracted", False):
        st.success(" Auto-extracted your new text!")
    if st.session_state.pop("human_override", False):
        st.success(" Human Override Accepted. AI telemetry corrected.")


def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        layout="wide",
        page_title="Yeti-Tracker: India Carbon Footprint Tracker",
        page_icon="",
    )
    st.title("Yeti-Tracker: Know Your Footprint")
    st.caption(
        "A hybrid AI + deterministic math engine that tracks your personal carbon "
        "footprint against India's factual per capita baseline of 2,500 kg CO2/year (World Bank)."
    )

    # Initialize typed state
    init_state(st.session_state)

    # We no longer seed demo history, ensuring a pristine blank slate
    # for the user to avoid premature "Anomaly" alerts on load.

    # 1. ALWAYS Run Math to get current deterministic state
    result = run_duckdb_math(
        st.session_state.get("car_km", 0),
        st.session_state.get("two_wheeler_km", 0),
        st.session_state.get("auto_rickshaw_km", 0),
        st.session_state.get("flight_km", 0),
        st.session_state.get("bus_km", 0),
        st.session_state.get("train_metro_km", 0),
        st.session_state.get("ac_hours", 0),
        st.session_state.get("restaurant_meals", 0),
        session_id=st.session_state.session_id,
    )
    tier_info = classify_tier(result.yearly_co2_kg)

    if st.session_state.get("run_math", False):
        _handle_math_success()

        append_history(
            st.session_state.session_id,
            result.yearly_co2_kg / 365.0,
            tier_info.tier,
        )

    # 2. Render 2-Column Grid
    col_left, col_right = st.columns([1.2, 1])
    with col_left:
        with st.container(border=True):
            _render_confessional(_handle_extract, _set_random_persona)

            if st.session_state.get("has_calculated", False):
                _render_top_progress_bars(result, tier_info)
                _render_asset_image(tier_info)

    with col_right:
        with st.container(border=True):
            _render_sliders(_handle_calculate, _handle_slider_change)

            total_monthly_savings = 0
            if st.session_state.get("has_calculated", False):
                st.markdown("---")
                total_monthly_savings = _render_bottom_advisor_dashboard(
                    result, tier_info, _handle_reply, _cached_advisor_call
                )

                if (
                    "cached_advice" in st.session_state
                    and st.session_state.cached_advice.roast
                ):
                    st.error(f"The Roast: {st.session_state.cached_advice.roast}")

    # 3. Render Financial Dashboard
    if st.session_state.get("has_calculated", False):
        with st.container(border=True):
            _render_financial_dashboard(result, total_monthly_savings, _toggle_rescue)
            _render_calculation_expander(result)

    if st.session_state.get("run_math", False):
        st.session_state.run_math = False

    # 5. Render History
    _render_history_section()


if __name__ == "__main__":
    main()
