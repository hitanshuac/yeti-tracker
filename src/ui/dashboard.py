"""
Dashboard rendering layer for the Yeti-Tracker financial and advisor panels.

Contains the Smart Advisor section, financial impact charts, and
alternatives table. Delegates all chart creation to ``chart_factory``
and all LLM interactions to ``llm_service``.
"""

import json
from typing import Callable

import pandas as pd
import streamlit as st

from src.carbon_engine import CarbonResult, TierClassification
from src.chart_factory import (
    create_doom_vs_rescue,
    create_gauge_chart,
    create_savings_waterfall,
)
from src.history import fetch_historical_kpis
from src.llm import AdvisorRequest, AdvisorResponse
from src.rag_service import fetch_rag_context


def _fetch_new_advice(
    result: CarbonResult,
    tier_info: TierClassification,
    on_advisor_call: Callable[[str], str],
) -> tuple[AdvisorResponse, str]:
    """Fetch fresh advisor advice from the LLM service.

    Args:
        result: Validated carbon calculation result.
        tier_info: Current gamification tier classification.
        on_advisor_call: Memoized callback wrapping the LLM advisor call.

    Returns:
        A tuple of (AdvisorResponse, rag_context_string).
    """
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
        ac_hours=st.session_state.get("ac_hours", 0),
        restaurant_meals=st.session_state.get("restaurant_meals", 0),
        tier=tier_info.tier,
        goal="Save money and stop the Yeti",
        kpis=json.dumps(kpis) if kpis else "No historical data.",
        worst_habit=result.worst_habit,
        rag_context=rag_context,
        raw_text=st.session_state.get("confessional_input", ""),
    )

    resp_json = on_advisor_call(req.model_dump_json())
    advice = AdvisorResponse.model_validate_json(resp_json)

    st.session_state.cached_advice = advice
    st.session_state.cached_rag_context = rag_context
    return advice, rag_context


def _render_bottom_advisor_dashboard(
    result: CarbonResult,
    tier_info: TierClassification,
    on_reply: Callable[[], None],
    on_advisor_call: Callable[[str], str],
) -> float:
    """Render the Smart Advisor section with advice and alternatives.

    Args:
        result: Validated carbon calculation result.
        tier_info: Current gamification tier classification.
        on_reply: Callback for user reply submissions.
        on_advisor_call: Memoized callback wrapping the LLM advisor call.

    Returns:
        Total monthly savings in INR from suggested alternatives.
    """
    st.markdown("###  The Smart Advisor")

    needs_new_advice = (
        st.session_state.get("run_math", False)
        or "cached_advice" not in st.session_state
    )

    if needs_new_advice:
        with st.spinner("Analyzing your financial doom..."):
            advice, _rag_context = _fetch_new_advice(result, tier_info, on_advisor_call)
    else:
        advice = st.session_state.cached_advice

    _render_feedback_ui(advice, tier_info, on_reply)

    total_monthly_savings = sum(a.est_monthly_savings_inr for a in advice.alternatives)

    if advice.alternatives:
        _render_alternatives_table(advice.alternatives)

    return total_monthly_savings


def _render_feedback_ui(
    advice: AdvisorResponse,
    tier_info: TierClassification,
    on_reply: Callable[[], None],
) -> None:
    """Render the advisor feedback interaction area.

    Args:
        advice: The current advisor response to display.
        tier_info: Current gamification tier classification.
        on_reply: Callback for user reply submissions.
    """
    st.info(f" **Yeti Advisor asks:** {advice.guilt_easing_question}")

    st.text_input(
        "Confess more...",
        key="reply_input",
        on_change=on_reply,
        placeholder="Type your response here and hit Enter...",
        help="Continue the conversation with the Yeti Advisor. Your reply will be appended to the confessional.",
    )


def _render_alternatives_table(alternatives: list) -> None:
    """Render the actionable alternatives as a styled table.

    Args:
        alternatives: List of AdvisorAlternative instances to display.
    """
    st.markdown("#### Adapt These TODAY (Instant Gratification)")
    alts_display = pd.DataFrame([a.model_dump() for a in alternatives]).rename(
        columns={
            "type": "Strategy",
            "alternative": "What To Do",
            "pros": "Pros",
            "cons": "Cons",
            "est_monthly_savings_inr": "Monthly Savings (INR)",
        }
    )
    alts_display["Monthly Savings (INR)"] = alts_display["Monthly Savings (INR)"].apply(
        lambda x: f"{x:,.0f}"
    )
    st.table(alts_display.set_index("Strategy"))


def _render_financial_dashboard(
    result: CarbonResult,
    total_monthly_savings: float,
    on_toggle_rescue: Callable[[], None],
) -> None:
    """Render the financial impact dashboard with stacked charts.

    Args:
        result: Validated carbon calculation result.
        total_monthly_savings: Total monthly savings from suggested alternatives.
        on_toggle_rescue: Callback to toggle between doom and rescue chart views.
    """
    monthly_tax = result.carbon_tax_inr / 12.0

    st.markdown("###  Financial Impact")
    st.markdown(
        f"You're burning **{monthly_tax:,.0f}/month** *(15% estimation variance)*  "
        f"but you could save **{total_monthly_savings:,.0f}/month** starting today."
    )

    col1, col2 = st.columns(2)
    with col1:
        gauge_max = max(25000, monthly_tax * 1.2)
        fig_tax = create_gauge_chart(
            monthly_tax, gauge_max, "Monthly Social Cost of Carbon (INR)"
        )
        st.plotly_chart(fig_tax, use_container_width=True)

    with col2:
        btn_label = (
            "Show My Doom"
            if st.session_state.get("show_rescue", False)
            else "Save Yourself"
        )
        st.button(btn_label, on_click=on_toggle_rescue, use_container_width=True)

        if st.session_state.get("show_rescue", False):
            fig = create_doom_vs_rescue(monthly_tax, total_monthly_savings)
        else:
            fig = create_savings_waterfall(monthly_tax, total_monthly_savings)
        st.plotly_chart(fig, use_container_width=True)
