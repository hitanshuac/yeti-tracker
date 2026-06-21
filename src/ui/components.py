import os

import pandas as pd
import streamlit as st

from src.chart_factory import create_history_chart
from src.history import fetch_history_dataframe


def _render_budget_bar(result) -> None:
    daily_kg = result.yearly_co2_kg / 365.0
    baseline_daily = 2500.0 / 365.0
    bar_ceiling = baseline_daily * 3.0
    budget_pct = min(1.0, max(0.01, daily_kg / bar_ceiling))

    if daily_kg <= baseline_daily:
        bar_color = "#00cc66"
        bar_label = f" {daily_kg:.1f} / {baseline_daily:.1f} kg  Within allowance"
    elif daily_kg <= baseline_daily * 2:
        bar_color = "#ffaa00"
        bar_label = f" {daily_kg:.1f} / {baseline_daily:.1f} kg  OVER allowance"
    else:
        bar_color = "#ff4b4b"
        bar_label = f" {daily_kg:.1f} / {baseline_daily:.1f} kg  CRITICAL OVERSHOOT"

    st.markdown("####  Daily Survival Allowance")
    st.markdown(
        f"<div title=' Everyone starts at 2,500 kg CO/year (India baseline). "
        f"The sliders track how much more your lifestyle adds on top.' "
        f"style='background:#222;border-radius:8px;overflow:hidden;height:32px;width:100%;position:relative;'>"
        f"<div style='background:{bar_color};width:{budget_pct * 100:.1f}%;height:100%;border-radius:8px;"
        f"transition:width 0.5s ease;'></div>"
        f"<span style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);"
        f"color:white;font-weight:bold;font-size:0.85em;white-space:nowrap;'>{bar_label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_tier_bar(result) -> None:
    current_co2 = result.yearly_co2_kg
    tier_max = 30000.0
    tier_pct = min(1.0, max(0.01, current_co2 / tier_max))

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

    tier_bar_label = f"{tier_label_text}  {current_co2:,.0f} / {tier_max:,.0f} kg"
    st.markdown("####  Session Tier Tracker")
    st.markdown(
        f"<div title='This bar tracks your total footprint. "
        f"Over 9,000 kg pushes you out of the Human tier into Catastrophes.' "
        f"style='background:#222;border-radius:8px;overflow:hidden;height:32px;width:100%;"
        f"position:relative;margin-bottom:8px;'>"
        f"<div style='background:{tier_bar_color};width:{tier_pct * 100:.1f}%;height:100%;border-radius:8px;"
        f"transition:width 0.8s ease;'></div>"
        f"<span style='position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);"
        f"color:white;font-weight:bold;font-size:0.85em;white-space:nowrap;'>{tier_bar_label}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _render_top_progress_bars(result, tier_info) -> None:
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

    _render_budget_bar(result)
    _render_tier_bar(result)

    if getattr(result, "is_anomaly", False):
        st.warning(
            "ANOMALY DETECTED: Your recent input deviates significantly from your historical baseline!"
        )


def _render_asset_image(tier_info) -> None:
    """Render the Yeti/Godzilla image."""
    st.markdown("###  Tier Status")
    if tier_info.image_path and os.path.exists(tier_info.image_path):
        if "Catastrophe" in tier_info.tier or "Warning" in tier_info.tier:
            with st.expander(" Reveal Catastrophe", expanded=False):
                st.image(
                    tier_info.image_path,
                    use_container_width=True,
                    caption=f"Tier: {tier_info.tier}",
                )
        else:
            st.image(
                tier_info.image_path,
                use_container_width=True,
                caption=f"Tier: {tier_info.tier}",
            )
    else:
        st.info("No asset available for this tier.")


def _render_sliders(on_calculate) -> None:
    """Render the human verification sliders."""
    st.markdown(
        "<h3 title='This tracks your variance above the 2,500kg India survival baseline.'>"
        "2. Human Verification</h3>",
        unsafe_allow_html=True,
    )

    if st.session_state.get("show_missing_electricity_prompt", False):
        st.info(
            " **Yeti extracted your data.** Verify the AC and sleep "
            "hours below  adjust if the AI missed anything."
        )

    if st.session_state.get("is_extracting", False):
        st.toast("Yeti extracted your data successfully!")
        st.session_state.is_extracting = False

    untracked = st.session_state.get("untracked_activities", [])
    if untracked:
        st.warning(
            f"**The Yeti noticed you do:** {', '.join(untracked)}. "
            "To maintain strict adherence to our verified MCAP dataset (Rule 5), we exclude unverified activities "
            "from your core calculation to prevent hallucinated scores."
        )
    c_max, f_max, t_max, r_max = 50000, 100000, 50000, 1095

    sc1, sc2 = st.columns(2)

    with sc1:
        st.slider(
            "Car (km/Yearly)",
            0,
            max(c_max, int(st.session_state.get("car_km", 0))),
            key="car_km",
            help="Total kilometers driven in a petrol/diesel car per year.",
        )
        st.slider(
            "Two-Wheeler / Bike (km/Yearly)",
            0,
            max(c_max, int(st.session_state.get("two_wheeler_km", 0))),
            key="two_wheeler_km",
            help="Total kilometers ridden on a scooter or motorcycle per year.",
        )
        st.slider(
            "Auto-Rickshaw / Cab (km/Yearly)",
            0,
            max(c_max, int(st.session_state.get("auto_rickshaw_km", 0))),
            key="auto_rickshaw_km",
            help="Total kilometers in an auto-rickshaw or taxi cab per year.",
        )

        st.slider(
            "Flight Kilometers (Yearly)",
            0,
            max(f_max, int(st.session_state.get("flight_km", 0))),
            key="flight_km",
            help="Total flight distance per year. Delhi-Mumbai one-way is ~1,400 km.",
        )

    with sc2:
        st.slider(
            "Bus Kilometers (Yearly)",
            0,
            max(t_max, int(st.session_state.get("bus_km", 0))),
            key="bus_km",
            help="Total km traveled by bus per year.",
        )
        st.slider(
            "Train/Metro Kilometers (Yearly)",
            0,
            max(t_max, int(st.session_state.get("train_metro_km", 0))),
            key="train_metro_km",
            help="Total km traveled by electric train or metro per year.",
        )
        st.slider(
            "Grid Drain (AC Hours)",
            0,
            max(24, int(st.session_state.get("ac_hours", 0)) * 2),
            key="ac_hours",
            help="Average hours of AC/cooler usage during the day and night.",
        )
        st.slider(
            "Restaurant Meals (Yearly)",
            0,
            max(r_max, int(st.session_state.get("restaurant_meals", 0))),
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
        on_click=on_calculate,
        help="Run the deterministic DuckDB math engine on your verified slider values.",
    )


def _render_history_section() -> None:
    """Render the confession history chart."""
    st.markdown("---")
    st.markdown("##  Your Confession History")

    try:
        history_df = fetch_history_dataframe(st.session_state.session_id)
        if not history_df.empty:
            fig = create_history_chart(history_df)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data yet. Confess your lifestyle to start tracking!")
    except Exception:
        st.info("Historical tracking will appear after your first confession.")


def _render_calculation_expander(result) -> None:
    """Render the calculation methodology in a full-width expander."""
    monthly_tax = result.carbon_tax_inr / 12.0
    with st.expander("How is this calculated?"):
        ex_col1, ex_col2 = st.columns([1, 1.5])

        with ex_col1:
            st.markdown("**Your Breakdown:**")
            for category, val_kg in result.breakdown.items():
                st.write(f"- **{category}:** {val_kg:,.0f} kg CO2/year")
            st.markdown("---")
            st.write(f"**Total Yearly:** {result.yearly_co2_kg:,.0f} kg CO2")
            st.write(
                f"**Yearly Tax:** {result.yearly_co2_kg:,.0f} kg x INR 15.80 = **INR {result.carbon_tax_inr:,.2f}**"
            )
            st.write(
                f"**Monthly Tax:** INR {result.carbon_tax_inr:,.2f} / 12 = **INR {monthly_tax:,.2f}**"
            )

        with ex_col2:
            st.markdown(
                "Your monthly tax is derived from the "
                "**Social Cost of Carbon (SCC)**  a globally accepted metric "
                "that estimates the economic damage caused by emitting 1 kg of CO2."
            )
            st.info(
                "**1 kg of CO2 = INR 15.80 in global climate damages** (Source: India GHG Platform, ISEC)"
            )

            st.markdown(
                "**Estimation Variance (15%):** Carbon footprint modeling inherently carries variance due to "
                "regional power grid mixes and specific hardware efficiency differences. While our DuckDB "
                "math engine is strictly deterministic based on your inputs, the final values represent "
                "an average baseline estimation."
            )

            st.markdown(
                "**Why is there a baseline?** Every person has an inescapable carbon "
                "footprint from basic survival: home-cooked meals, shelter electricity "
                "(lights, fridge, fans), water supply, and shared infrastructure. "
                "India's per capita average is a factual **2,500 kg CO2/year** "
                "(World Bank). The sliders above track your **additional** lifestyle "
                "impact on top of this baseline."
            )

            st.markdown(
                "**How are Spikes Calculated?**\n"
                "Spikes are calculated strictly mathematically using a **90th Percentile** window function "
                "over your last 30 days of data in DuckDB (`PERCENTILE_CONT(0.9)`). "
                "No AI hallucinationjust pure statistics."
            )

        st.markdown("---")
        st.markdown("**Emission Sources & Agencies**")
        st.markdown(
            "This tool uses verified regional data sources to ensure a deterministic math engine."
        )
        try:
            factors_df = pd.read_csv("data/carbon_factors.csv")
            display_df = factors_df[
                ["activity", "co2_kg_per_unit", "source_agency", "description"]
            ]
            display_df.columns = ["Activity", "CO2 (kg/unit)", "Agency", "Description"]
            st.dataframe(display_df, hide_index=True, use_container_width=True)
        except (FileNotFoundError, KeyError):
            st.warning("Could not load carbon factors table.")


def _render_confessional(on_extract, on_demo) -> None:
    """Render the confessional input box and buttons."""
    st.markdown(
        "<h3 title='The AI extracts unstructured text into exact integers for the math engine.'>"
        "1. The Confessional (LLM Auto-Fill)</h3>",
        unsafe_allow_html=True,
    )
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
            on_click=on_extract,
            use_container_width=True,
            help="Send your text to the AI parser. It will auto-fill the sliders.",
        )
    with c2:
        st.button(
            "Try a Demo Persona",
            on_click=on_demo,
            use_container_width=True,
            help="Load a pre-written lifestyle example to see how the tracker works.",
        )
