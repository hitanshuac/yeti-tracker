# pylint: disable=line-too-long,broad-exception-caught
"""
Yeti-Tracker: Personal Carbon Footprint Gamification Dashboard.

This file is a **thin UI orchestrator** — it defines the Streamlit layout,
widgets, and callbacks but delegates all business logic to the ``src/`` modules.
"""

import json
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
from src.llm_service import AdvisorRequest, AdvisorResponse, get_advisor_response, parse_confession
from src.rag_service import fetch_rag_context
from src.state_manager import init_state

# ---------------------------------------------------------------------------
# Callbacks (thin wrappers that update session_state)
# ---------------------------------------------------------------------------


def _handle_extract() -> bool:
    """Parse the confessional text and populate slider values."""
    messy = st.session_state.get("confessional_input", "")
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
    st.session_state.daily_sleep_hours = getattr(parsed, "daily_sleep_hours", 8)
    st.session_state.sleep_ac_on = getattr(parsed, "sleep_ac_on", False)
    st.session_state.daytime_ac_hours = getattr(parsed, "daytime_ac_hours", 0)
    st.session_state.restaurant_meals = getattr(parsed, "restaurant_meals", 0)
    st.session_state.untracked_activities = getattr(parsed, "untracked_activities", [])

    # Save AI baselines for SRE Override tracking
    st.session_state.ai_car_km = st.session_state.car_km
    st.session_state.ai_two_wheeler_km = st.session_state.two_wheeler_km
    st.session_state.ai_auto_rickshaw_km = st.session_state.auto_rickshaw_km
    st.session_state.ai_flight_km = st.session_state.flight_km
    st.session_state.ai_bus_km = st.session_state.bus_km
    st.session_state.ai_train_metro_km = st.session_state.train_metro_km
    st.session_state.ai_daily_sleep_hours = st.session_state.daily_sleep_hours
    st.session_state.ai_sleep_ac_on = st.session_state.sleep_ac_on
    st.session_state.ai_daytime_ac_hours = st.session_state.daytime_ac_hours
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
    messy = st.session_state.get("confessional_input", "")
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
        ("daily_sleep_hours", "ai_daily_sleep_hours", 8),
        ("sleep_ac_on", "ai_sleep_ac_on", False),
        ("daytime_ac_hours", "ai_daytime_ac_hours", 0),
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


def _set_random_persona() -> None:
    """Set a random demo persona with hardcoded values — zero LLM calls."""
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
            "daily_sleep_hours": 8,
            "sleep_ac_on": False,
            "daytime_ac_hours": 0,
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
            "daily_sleep_hours": 7,
            "sleep_ac_on": True,
            "daytime_ac_hours": 120,
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
            "daily_sleep_hours": 6,
            "sleep_ac_on": True,
            "daytime_ac_hours": 4,
            "restaurant_meals": 365,
        },
        {
            "name": "The Eco-Warrior",
            "text": ("The Eco-Warrior: I ride my bike to work. No AC. Eat out maybe once a month. No flights."),
            "car_km": 0,
            "two_wheeler_km": 2600,
            "auto_rickshaw_km": 0,
            "flight_km": 0,
            "bus_km": 0,
            "train_metro_km": 2600,
            "daily_sleep_hours": 8,
            "sleep_ac_on": False,
            "daytime_ac_hours": 0,
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
            "daily_sleep_hours": 8,
            "sleep_ac_on": True,
            "daytime_ac_hours": 8,
            "restaurant_meals": 104,
        },
    ]
    persona = random.choice(personas)
    st.session_state.confessional_input = persona["text"]
    for key in [
        "car_km",
        "two_wheeler_km",
        "auto_rickshaw_km",
        "flight_km",
        "bus_km",
        "train_metro_km",
        "daily_sleep_hours",
        "sleep_ac_on",
        "daytime_ac_hours",
        "restaurant_meals",
    ]:
        st.session_state[key] = persona[key]
    # Auto-trigger calculation — no LLM needed
    st.session_state.run_math = True
    st.session_state.has_calculated = True
    st.session_state.show_missing_electricity_prompt = False


def _toggle_rescue() -> None:
    """Toggle between doom and rescue chart views."""
    st.session_state.show_rescue = not st.session_state.show_rescue


# ---------------------------------------------------------------------------
# UI Sections
# ---------------------------------------------------------------------------


def _render_gamification_header(result, tier_info) -> None:
    """Render the top gamification banner, budget bar, and tier progress."""
    if tier_info.tier == "Category 3 Catastrophe":
        st.markdown(
            """
            <style>
            .stApp {
                background-color: #3b0000 !important;
                color: #ffcccc !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<h1 style='text-align: center; color: {tier_info.color}; "
        f"font-size: 3.5em;' role='status' aria-live='polite'>{tier_info.message}</h1>",
        unsafe_allow_html=True,
    )

    # --- Budget Bar: Daily Survival Allowance ---
    daily_kg = result.yearly_co2_kg / 365.0
    baseline_daily = 2500.0 / 365.0  # 6.8 kg/day
    # Scale: 0 → baseline = green zone, baseline → 3x baseline = red zone
    bar_ceiling = baseline_daily * 3.0  # ~20.5 kg/day = visual max
    budget_pct = min(1.0, max(0.01, daily_kg / bar_ceiling))

    if daily_kg <= baseline_daily:
        bar_color = "#00cc66"  # green — under budget
        bar_label = f"✅ {daily_kg:.1f} / {baseline_daily:.1f} kg — Within allowance"
    elif daily_kg <= baseline_daily * 2:
        bar_color = "#ffaa00"  # amber — over budget
        bar_label = f"⚠️ {daily_kg:.1f} / {baseline_daily:.1f} kg — OVER allowance"
    else:
        bar_color = "#ff4b4b"  # red — catastrophic
        bar_label = f"🔥 {daily_kg:.1f} / {baseline_daily:.1f} kg — CRITICAL OVERSHOOT"

    st.markdown("#### ⏳ Daily Survival Allowance")
    st.markdown(
        f"<div style='background:#222;border-radius:8px;overflow:hidden;height:32px;width:100%;position:relative;'>"
        f"<div style='background:{bar_color};width:{budget_pct * 100:.1f}%;height:100%;border-radius:8px;"
        f"transition:width 0.5s ease;'></div>"
        f"<span style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);"
        f"color:white;font-weight:bold;font-size:0.85em;white-space:nowrap;'>{bar_label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # --- Tier Progress Bar: Current calculation ---
    current_co2 = result.yearly_co2_kg
    tier_max = 30000.0  # Category 3 threshold
    tier_pct = min(1.0, max(0.01, current_co2 / tier_max))

    # Determine tier color for progress bar
    if current_co2 <= 9000:
        tier_bar_color = "#00cc66"
        tier_label_text = "Human"
    elif current_co2 <= 15000:
        tier_bar_color = "#ffd700"
        tier_label_text = "Cat 1 Warning"
    elif current_co2 <= 30000:
        tier_bar_color = "#ffaa00"
        tier_label_text = "Cat 2 Catastrophe"
    else:
        tier_bar_color = "#ff4b4b"
        tier_label_text = "Cat 3 Catastrophe"

    tier_bar_label = f"{tier_label_text} — {current_co2:,.0f} / {tier_max:,.0f} kg"
    st.markdown("#### 📊 Session Tier Tracker")
    st.markdown(
        f"<div style='background:#222;border-radius:8px;overflow:hidden;height:32px;width:100%;"
        f"position:relative;margin-bottom:8px;'>"
        f"<div style='background:{tier_bar_color};width:{tier_pct * 100:.1f}%;height:100%;border-radius:8px;"
        f"transition:width 0.8s ease;'></div>"
        f"<span style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);"
        f"color:white;font-weight:bold;font-size:0.85em;white-space:nowrap;'>{tier_bar_label}</span>"
        f"</div>",
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


@st.cache_data(show_spinner=False)
def _cached_advisor_call(req_json: str) -> str:
    """Memoize LLM calls to prevent thread blocking."""
    req = AdvisorRequest.model_validate_json(req_json)
    return get_advisor_response(req).model_dump_json()


def _render_advisor_section(result, tier_info) -> None:
    """Render the Smart Advisor section with advice and alternatives."""
    st.markdown("---")
    st.markdown("### 🎙️ The Smart Advisor")

    needs_new_advice = st.session_state.get("run_math", False) or "cached_advice" not in st.session_state

    if needs_new_advice:
        with st.spinner("Analyzing your financial doom..."):
            rag_context = fetch_rag_context(st.session_state.get("confessional_input", ""))
            kpis = fetch_historical_kpis(st.session_state.session_id)
            req = AdvisorRequest(
                carbon=result.yearly_co2_kg,
                tax=result.carbon_tax_inr,
                car_km=st.session_state.get("car_km", 0),
                two_wheeler_km=st.session_state.get("two_wheeler_km", 0),
                auto_rickshaw_km=st.session_state.get("auto_rickshaw_km", 0),
                flight_km=st.session_state.get("flight_km", 0),
                bus_km=st.session_state.get("bus_km", 0),
                train_metro_km=st.session_state.get("train_metro_km", 0),
                daily_sleep_hours=st.session_state.get("daily_sleep_hours", 8),
                sleep_ac_on=st.session_state.get("sleep_ac_on", False),
                daytime_ac_hours=st.session_state.get("daytime_ac_hours", 0),
                restaurant_meals=st.session_state.get("restaurant_meals", 0),
                tier=tier_info.tier,
                goal="Save money and stop the Yeti",
                kpis=json.dumps(kpis) if kpis else "No historical data.",
                worst_habit=result.worst_habit,
                rag_context=rag_context,
                raw_text=st.session_state.get("confessional_input", ""),
            )

            resp_json = _cached_advisor_call(req.model_dump_json())
            advice = AdvisorResponse.model_validate_json(resp_json)

            st.session_state.cached_advice = advice
            st.session_state.cached_rag_context = rag_context
    else:
        advice = st.session_state.cached_advice
        rag_context = st.session_state.cached_rag_context

    # Guilt Easing Component
    st.info(f"🗣️ **Yeti Advisor asks:** {advice.guilt_easing_question}")
    st.success(f"☀️ **Silver Lining:** {advice.silver_lining}")

    # Only trigger roasts if the user hits the upper tiers (not Human)
    if tier_info.tier != "Human":
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
        f"### 💸 You're burning **₹{monthly_tax:,.0f}/month** *(±15% estimation variance)* — "
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
            st.info("**1 kg of CO2 = INR 15.80 in global climate damages** (Source: India GHG Platform, ISEC)")
            st.markdown("---")
            st.markdown("**Emission Sources & Agencies**")
            st.markdown("This tool uses verified regional data sources to ensure a deterministic math engine.")
            try:
                factors_df = pd.read_csv("data/carbon_factors.csv")
                display_df = factors_df[["activity", "co2_kg_per_unit", "source_agency", "description"]]
                display_df.columns = ["Activity", "CO2 (kg/unit)", "Agency", "Description"]
                st.dataframe(display_df, hide_index=True)
            except (FileNotFoundError, KeyError):
                st.warning("Could not load carbon factors table.")
            st.markdown("---")
            st.markdown(
                "**Estimation Variance (±15%):** Carbon footprint modeling inherently carries variance due to "
                "regional power grid mixes and specific hardware efficiency differences. While our DuckDB math engine "
                "is strictly deterministic based on your inputs, the final values represent an average baseline estimation."
            )
            st.markdown("---")
            st.markdown(
                "**Why is there a baseline?** Every person has an inescapable carbon "
                "footprint from basic survival: home-cooked meals, shelter electricity "
                "(lights, fridge, fans), water supply, and shared infrastructure. "
                "India's per capita average is a factual **2,500 kg CO2/year** "
                "(World Bank). The sliders above track your **additional** lifestyle "
                "impact on top of this baseline."
            )
            st.markdown("---")
            st.markdown(
                "**How are Spikes Calculated?**\n"
                "Spikes are calculated strictly mathematically using a **90th Percentile** window function "
                "over your last 30 days of data in DuckDB (`PERCENTILE_CONT(0.9)`). "
                "No AI hallucination—just pure statistics."
            )
            st.markdown("---")
            st.markdown("**Your Breakdown:**")
            for category, val_kg in result.breakdown.items():
                st.write(f"- **{category}:** {val_kg:,.0f} kg CO2/year")
            st.markdown("---")
            st.write(f"**Total Yearly:** {result.yearly_co2_kg:,.0f} kg CO2")
            st.write(
                f"**Yearly Tax:** {result.yearly_co2_kg:,.0f} kg x INR 15.80 = **INR {result.carbon_tax_inr:,.2f}**"
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
            placeholder=(
                "e.g. I drove 15km to work today, ran the AC for about 4 hours "
                "in the afternoon, and ate at a restaurant for dinner. "
                "I usually sleep 8 hours with the AC off."
            ),
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
        st.caption(
            "🏠 **Everyone starts at 2,500 kg CO₂/year** (India baseline). "
            "The sliders track how much *more* your lifestyle adds on top."
        )

        if st.session_state.get("show_missing_electricity_prompt", False):
            st.info(
                "🔌 **Yeti extracted your data.** Verify the AC and sleep "
                "hours below — adjust if the AI missed anything."
            )

        if st.session_state.get("is_extracting", False):
            st.toast("Yeti extracted your data successfully!", icon="✅")
            st.session_state.is_extracting = False

        untracked = st.session_state.get("untracked_activities", [])
        if untracked:
            st.warning(
                f"**The Yeti noticed you do:** {', '.join(untracked)}. "
                "To maintain strict adherence to our verified MCAP dataset (Rule 5), we exclude unverified activities "
                "from your core calculation to prevent hallucinated scores.",
                icon="🚧",
            )
        c_max, f_max, t_max, r_max = 50000, 100000, 50000, 1095

        st.markdown("#### Fossil Fuel Transport")
        st.slider(
            "Car (km/Yearly)",
            0,
            max(c_max, st.session_state.car_km),
            key="car_km",
            help="Total kilometers driven in a petrol/diesel car per year.",
        )
        st.slider(
            "Two-Wheeler / Bike (km/Yearly)",
            0,
            max(c_max, st.session_state.get("two_wheeler_km", 0)),
            key="two_wheeler_km",
            help="Total kilometers ridden on a scooter or motorcycle per year.",
        )
        st.slider(
            "Auto-Rickshaw / Cab (km/Yearly)",
            0,
            max(c_max, st.session_state.get("auto_rickshaw_km", 0)),
            key="auto_rickshaw_km",
            help="Total kilometers in an auto-rickshaw or taxi cab per year.",
        )
        st.markdown("#### Other Transport")
        st.slider(
            "Flight Kilometers (Yearly)",
            0,
            max(f_max, st.session_state.flight_km),
            key="flight_km",
            help="Total flight distance per year. Delhi-Mumbai one-way is ~1,400 km.",
        )
        st.slider(
            "Bus Kilometers (Yearly)",
            0,
            max(t_max, st.session_state.get("bus_km", 0)),
            key="bus_km",
            help="Total km traveled by bus per year.",
        )
        st.slider(
            "Train/Metro Kilometers (Yearly)",
            0,
            max(t_max, st.session_state.get("train_metro_km", 0)),
            key="train_metro_km",
            help="Total km traveled by electric train or metro per year.",
        )
        st.slider(
            "Daily Sleep Hours",
            0,
            24,
            st.session_state.get("daily_sleep_hours", 8),
            key="daily_sleep_hours",
            help="Average hours of sleep per night. We use this to calculate your minimum baseline.",
        )
        st.checkbox(
            "Sleep with AC/Cooler on?",
            value=st.session_state.get("sleep_ac_on", False),
            key="sleep_ac_on",
            help="Do you leave the AC or cooler running while you sleep?",
        )
        st.slider(
            "Grid Drain (Daytime AC Hours)",
            0,
            max(24, st.session_state.get("daytime_ac_hours", 0) * 2),
            st.session_state.get("daytime_ac_hours", 0),
            key="daytime_ac_hours",
            help="Average hours of AC/cooler usage during the day while awake.",
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
        if st.session_state.pop("human_override", False):
            st.success("👨‍💻 Human Override Accepted. AI telemetry corrected.")

    result = run_duckdb_math(
        st.session_state.get("car_km", 0),
        st.session_state.get("two_wheeler_km", 0),
        st.session_state.get("auto_rickshaw_km", 0),
        st.session_state.get("flight_km", 0),
        st.session_state.get("bus_km", 0),
        st.session_state.get("train_metro_km", 0),
        st.session_state.get("daily_sleep_hours", 8),
        st.session_state.get("sleep_ac_on", False),
        st.session_state.get("daytime_ac_hours", 0),
        st.session_state.get("restaurant_meals", 0),
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

    total_monthly_savings = _render_advisor_section(result, tier_info)
    _render_financial_dashboard(result, total_monthly_savings)

    # Reset the flag AFTER all sub-sections have used it to determine if they should run API calls
    if st.session_state.get("run_math", False):
        st.session_state.run_math = False


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
        "footprint against India's factual per capita baseline of 2,500 kg CO2/year (World Bank)."
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
