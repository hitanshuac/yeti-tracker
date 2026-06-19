"""
Yeti-Tracker: Personal Carbon Footprint Gamification Dashboard.

This file is a **thin UI orchestrator** — it defines the Streamlit layout,
widgets, and callbacks but delegates all business logic to the ``src/`` modules.
"""

import os
import random

import pandas as pd
import streamlit as st

from src.carbon_engine import classify_tier, run_duckdb_math
from src.chart_factory import (
    create_doom_vs_rescue,
    create_gauge_chart,
    create_history_chart,
    create_savings_waterfall,
)
from src.history import (
    append_history,
    fetch_historical_kpis,
    fetch_history_dataframe,
    seed_demo_history,
)
from src.llm_service import get_advisor_response, parse_confession
from src.rag_service import fetch_rag_context
from src.state_manager import init_state

# ---------------------------------------------------------------------------
# Callbacks (thin wrappers that update session_state)
# ---------------------------------------------------------------------------


def _handle_extract() -> None:
    """Parse the confessional text and populate slider values."""
    messy = st.session_state.get("confessional_input", "")
    st.session_state.last_extracted_text = messy
    parsed = parse_confession(messy)
    st.session_state.car_km = parsed.car_km
    st.session_state.flight_km = parsed.flight_km
    st.session_state.transit_km = parsed.transit_km
    st.session_state.ac_hours = parsed.ac_hours
    st.session_state.restaurant_meals = parsed.restaurant_meals


def _handle_reply() -> None:
    """Append the user's reply to confessional and re-extract."""
    reply = st.session_state.get("reply_input", "")
    if reply:
        st.session_state.confessional_input += f"\n\nYeti Advisor Response: {reply}"
        st.session_state.reply_input = ""
        _handle_extract()
        st.session_state.auto_extracted = True
        st.session_state.run_math = True
        st.session_state.has_calculated = True


def _handle_calculate() -> None:
    """Trigger the calculation pipeline."""
    messy = st.session_state.get("confessional_input", "")
    last = st.session_state.get("last_extracted_text", "")
    if messy != last:
        _handle_extract()
        st.session_state.auto_extracted = True
    st.session_state.run_math = True
    st.session_state.has_calculated = True


def _set_random_persona() -> None:
    """Set a random demo persona into the confessional."""
    personas = [
        (
            "The Commuter: I drive about 30 km to the office in Andheri every weekday. "
            "No flights. Eat out once a week at a local restaurant."
        ),
        (
            "The Crypto Bro: I run 5 AC units 24/7 for my mining rig in Pune. "
            "I eat out 3 times a day. I fly business class to Goa once a month."
        ),
        (
            "The Corporate Jetsetter: I fly Delhi-Bangalore every week for work. "
            "I take Ola everywhere (maybe 80 km a week). Eat out every day."
        ),
        ("The Eco-Warrior: I ride my bike to work. No AC. " "Eat out maybe once a month. No flights."),
        (
            "The Suburbanite: I drive an SUV about 60 km a day in Noida for errands. "
            "Keep the AC blasted all summer. Fly to Kerala once a year for vacation."
        ),
    ]
    st.session_state.confessional_input = random.choice(personas)


def _toggle_rescue() -> None:
    """Toggle between doom and rescue chart views."""
    st.session_state.show_rescue = not st.session_state.show_rescue


# ---------------------------------------------------------------------------
# UI Sections
# ---------------------------------------------------------------------------


def _render_gamification_header(result, tier_info) -> None:
    """Render the top gamification banner and tier image."""
    st.markdown(
        f"<h1 style='text-align: center; color: {tier_info.color}; "
        f"font-size: 3.5em;' role='status' aria-live='polite'>{tier_info.message}</h1>",
        unsafe_allow_html=True,
    )
    if getattr(result, "is_anomaly", False):
        st.warning("ANOMALY DETECTED: Your recent input deviates significantly from your historical baseline!")
    if tier_info.image_path and os.path.exists(tier_info.image_path):
        st.image(
            tier_info.image_path,
            use_container_width=True,
            caption=f"Tier: {tier_info.tier}",
        )


def _render_advisor_section(result, tier_info) -> None:
    """Render the Smart Advisor section with advice and alternatives."""
    st.markdown("---")
    st.markdown("### 🎙️ The Smart Advisor")

    c_km = st.session_state.car_km
    f_km = st.session_state.flight_km
    t_km = st.session_state.transit_km
    a_hours = st.session_state.ac_hours
    r_meals = st.session_state.restaurant_meals

    with st.spinner("Analyzing your financial doom..."):
        rag_context = fetch_rag_context(st.session_state.get("confessional_input", ""))
        kpis = fetch_historical_kpis(st.session_state.session_id)
        advice = get_advisor_response(
            result.yearly_co2_kg,
            result.carbon_tax_inr,
            c_km,
            f_km,
            t_km,
            a_hours,
            r_meals,
            tier_info.tier,
            "Save the Planet",
            kpis,
            rag_context,
        )

        # Guilt Easing Component
        st.info(f"🗣️ **Yeti Advisor asks:** {advice.guilt_easing_question}")
        st.success(f"☀️ **Silver Lining:** {advice.silver_lining}")
        st.error(f"🔥 **The Roast:** {advice.roast}")

        # Feedback Loop Input
        st.text_input(
            "Confess more...",
            key="reply_input",
            on_change=_handle_reply,
            placeholder="Type your response here and hit Enter...",
            help="Continue the conversation with the Yeti Advisor. Your reply will be appended to the confessional.",
        )

        total_monthly_savings = sum(a.est_monthly_savings_inr for a in advice.alternatives)

        if advice.alternatives:
            st.markdown("#### Adapt These TODAY (Instant Gratification)")
            alts_display = pd.DataFrame([a.model_dump() for a in advice.alternatives]).rename(
                columns={
                    "type": "Strategy",
                    "alternative": "What To Do",
                    "pros": "Pros",
                    "cons": "Cons",
                    "est_monthly_savings_inr": "Monthly Savings (INR)",
                }
            )
            st.table(alts_display.set_index("Strategy"))

    return total_monthly_savings


def _render_financial_dashboard(result, total_monthly_savings) -> None:
    """Render the financial impact dashboard with charts."""
    monthly_tax = result.carbon_tax_inr / 12.0

    st.markdown("---")
    st.markdown(
        f"### 💸 You're burning **₹{monthly_tax:,.0f}/month** — "
        f"but you could save **₹{total_monthly_savings:,.0f}/month** starting today."
    )

    btn_label = "💀 Show My Doom" if st.session_state.show_rescue else "🛡️ Save Yourself"
    st.button(btn_label, on_click=_toggle_rescue, use_container_width=True)

    mc1, mc2 = st.columns(2)
    with mc1:
        st.markdown("### Monthly Carbon Tax")
        gauge_max = max(25000, monthly_tax * 1.2)
        fig_tax = create_gauge_chart(monthly_tax, gauge_max, "Monthly Social Cost of Carbon (INR)")
        st.plotly_chart(fig_tax, use_container_width=True)

        with st.expander("How is this calculated?"):
            st.markdown(
                "Your monthly tax is derived from the "
                "**Social Cost of Carbon (SCC)** — a globally accepted metric "
                "that estimates the economic damage caused by emitting 1 kg of CO2."
            )
            st.info("**1 kg of CO2 = INR 15.80 in global climate damages** " "(Source: India GHG Platform, ISEC)")
            st.markdown("---")
            st.markdown(
                "**Why is there a baseline?** Every person has an inescapable carbon "
                "footprint from basic survival: home-cooked meals, shelter electricity "
                "(lights, fridge, fans), water supply, and shared infrastructure. "
                "India's per capita average is approximately **1,500 kg CO2/year** "
                "(ISEC study). The sliders above track your **additional** lifestyle "
                "impact on top of this baseline."
            )
            st.markdown("---")
            st.markdown("**Your Breakdown:**")
            for category, val_kg in result.breakdown.items():
                st.write(f"- **{category}:** {val_kg:,.0f} kg CO2/year")
            st.markdown("---")
            st.write(f"**Total Yearly:** {result.yearly_co2_kg:,.0f} kg CO2")
            st.write(
                f"**Yearly Tax:** {result.yearly_co2_kg:,.0f} kg x INR 15.80 = " f"**INR {result.carbon_tax_inr:,.2f}**"
            )
            st.write(f"**Monthly Tax:** INR {result.carbon_tax_inr:,.2f} / 12 = **INR {monthly_tax:,.2f}**")

    with mc2:
        if st.session_state.show_rescue:
            st.markdown("### 🛡️ Your Rescue Plan")
            fig = create_doom_vs_rescue(monthly_tax, total_monthly_savings)
        else:
            st.markdown("### 💀 The Damage")
            fig = create_savings_waterfall(monthly_tax, total_monthly_savings)
        st.plotly_chart(fig, use_container_width=True)


def _render_input_section() -> None:
    """Render the confessional + sliders input section."""
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 1. The Confessional (LLM Auto-Fill)")
        st.text_area(
            "Confess your lifestyle:",
            height=100,
            key="confessional_input",
            help=(
                "Describe your daily habits in plain English. The AI will extract "
                "transport distances, AC usage, and dining frequency automatically."
            ),
        )
        c1, c2 = st.columns(2)
        with c1:
            st.button(
                "Extract Data",
                type="primary",
                on_click=_handle_extract,
                use_container_width=True,
                help="Send your text to the AI parser. It will auto-fill the sliders.",
            )
        with c2:
            st.button(
                "Try a Demo Persona",
                on_click=_set_random_persona,
                use_container_width=True,
                help="Load a pre-written lifestyle example to see how the tracker works.",
            )

    with col2:
        st.markdown("### 2. Human Verification")
        st.info(
            "The math engine ONLY uses these deterministic sliders. "
            "Verify the AI extraction is correct before calculating."
        )

        c_max, f_max, t_max, a_max, r_max = 50000, 100000, 50000, 8760, 1095

        st.slider(
            "Car Kilometers (Yearly)",
            0,
            max(c_max, st.session_state.car_km),
            key="car_km",
            help="Total km driven by private car per year. India avg: ~7,000 km.",
        )
        st.slider(
            "Flight Kilometers (Yearly)",
            0,
            max(f_max, st.session_state.flight_km),
            key="flight_km",
            help="Total flight distance per year. Delhi-Mumbai one-way is ~1,400 km.",
        )
        st.slider(
            "Public Transit Kilometers (Yearly)",
            0,
            max(t_max, st.session_state.transit_km),
            key="transit_km",
            help="Total km by bus, train, or metro per year.",
        )
        st.slider(
            "AC / Heating Hours (Yearly)",
            0,
            max(a_max, st.session_state.ac_hours),
            key="ac_hours",
            help="Total hours of air conditioning per year. 8 hrs/day for 6 months = ~1,460 hrs.",
        )
        st.slider(
            "Restaurant Meals (Yearly)",
            0,
            max(r_max, st.session_state.restaurant_meals),
            key="restaurant_meals",
            help=(
                "Number of restaurant/takeaway meals per year. "
                "This tracks EXTRA impact above your home-cooked baseline."
            ),
        )

        st.button(
            "Calculate Financial Impact",
            type="primary",
            use_container_width=True,
            on_click=_handle_calculate,
            help="Run the deterministic DuckDB math engine on your verified slider values.",
        )


def _render_history_section() -> None:
    """Render the confession history chart."""
    st.markdown("---")
    st.markdown("## 📈 Your Confession History")

    try:
        history_df = fetch_history_dataframe(st.session_state.session_id)
        if not history_df.empty:
            fig = create_history_chart(history_df)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data yet. Confess your lifestyle to start tracking!")
    except Exception:
        st.info("Historical tracking will appear after your first confession.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def _render_results_section() -> None:
    """Render the calculation results, advisor, and dashboard."""
    if st.session_state.get("run_math", False):
        if st.session_state.pop("auto_extracted", False):
            st.success("✅ Auto-extracted your new text!")

    result = run_duckdb_math(
        st.session_state.car_km,
        st.session_state.flight_km,
        st.session_state.transit_km,
        st.session_state.ac_hours,
        st.session_state.restaurant_meals,
        session_id=st.session_state.session_id,
    )
    tier_info = classify_tier(result.yearly_co2_kg)

    _render_gamification_header(result, tier_info)

    if st.session_state.get("run_math", False):
        append_history(
            st.session_state.session_id,
            result.yearly_co2_kg / 365.0,
            tier_info.tier,
        )
        st.session_state.run_math = False

    total_monthly_savings = _render_advisor_section(result, tier_info)
    _render_financial_dashboard(result, total_monthly_savings)


def main() -> None:
    """Main application entry point."""
    st.set_page_config(
        layout="wide",
        page_title="Yeti-Tracker: India Carbon Footprint Tracker",
        page_icon="🌍",
    )
    st.title("Yeti-Tracker: Know Your Footprint")
    st.caption(
        "A hybrid AI + deterministic math engine that tracks your personal carbon "
        "footprint against India's per capita baseline of 1,500 kg CO2/year."
    )

    # Initialize typed state
    init_state(st.session_state)

    # Seed demo history once per session
    if not st.session_state.get("history_seeded", False):
        seed_demo_history(st.session_state.session_id)
        st.session_state.history_seeded = True

    # --- Results Section (only after calculation) ---
    if st.session_state.get("has_calculated", False):
        _render_results_section()

    # --- Input Section (always visible) ---
    st.markdown("---")
    _render_input_section()

    # --- History Section ---
    _render_history_section()


if __name__ == "__main__":
    main()
