"""
Plotly chart factory for the Yeti-Tracker dashboard.

All chart creation logic is centralized here  pure functions that
accept data and return Plotly Figure objects.  No Streamlit, no DB, no LLM.
"""

import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Shared theme constants
# ---------------------------------------------------------------------------

_BG = "#0e1117"
_FONT = {"color": "white", "family": "Arial"}
_GRID = "#333333"


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def create_gauge_chart(value: float, max_value: float, title: str) -> go.Figure:
    """Create a gauge chart for monthly carbon tax.

    Args:
        value: Current metric value.
        max_value: Maximum gauge range.
        title: Chart title.

    Returns:
        A Plotly Figure.
    """
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
        paper_bgcolor=_BG,
        font=_FONT,
        height=380,
        margin={"l": 20, "r": 20, "b": 20, "t": 50},
    )
    return fig


def create_savings_waterfall(monthly_tax: float, savings: float) -> go.Figure:
    """Waterfall chart: Current Tax  Savings  Optimized Tax.

    Args:
        monthly_tax: Monthly carbon tax in INR.
        savings: Monthly savings from alternatives in INR.

    Returns:
        A Plotly Figure.
    """
    optimized = max(0, monthly_tax - savings)
    weekly_saved = savings / 4.33
    quarterly_saved = savings * 3

    fig = go.Figure(
        go.Waterfall(
            name="Monthly Impact",
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=["Your Monthly Tax", "AI Savings Plan", "After Rescue"],
            y=[monthly_tax, -savings, optimized],
            text=[
                f"{monthly_tax:,.0f}",
                f"-{savings:,.0f}",
                f"{optimized:,.0f}",
            ],
            textposition="outside",
            connector={"line": {"color": "#555"}},
            decreasing={"marker": {"color": "#00cc66"}},
            increasing={"marker": {"color": "#ff4b4b"}},
            totals={"marker": {"color": "#3b82f6"}},
        )
    )
    pct = (savings / monthly_tax * 100) if monthly_tax > 0 else 0
    fig.update_layout(
        title={
            "text": (
                f"You save {weekly_saved:,.0f}/wk  {savings:,.0f}/mo "
                f" {quarterly_saved:,.0f}/qtr ({pct:.0f}% reduction)"
            ),
            "font": {"color": "#00cc66", "size": 14},
        },
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=_FONT,
        height=380,
        margin={"l": 20, "r": 20, "b": 20, "t": 60},
        showlegend=False,
    )
    fig.update_yaxes(gridcolor=_GRID, title="INR / Month")
    return fig


def create_doom_vs_rescue(monthly_tax: float, savings: float) -> go.Figure:
    """12-month projection: doom trajectory vs rescue trajectory.

    Args:
        monthly_tax: Monthly carbon tax in INR.
        savings: Monthly savings from alternatives in INR.

    Returns:
        A Plotly Figure.
    """
    months = [f"Month {i}" for i in range(1, 13)]
    doom = [monthly_tax * i for i in range(1, 13)]
    optimized_monthly = monthly_tax - savings
    rescue = [optimized_monthly * i for i in range(1, 13)]
    cumulative_saved = [(monthly_tax - optimized_monthly) * i for i in range(1, 13)]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=doom,
            mode="lines+markers",
            name=" Current Path",
            line={"color": "#ff4b4b", "width": 3},
            fill=None,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=months,
            y=rescue,
            mode="lines+markers",
            name=" After Rescue",
            line={"color": "#00cc66", "width": 3},
        )
    )
    fig.add_trace(
        go.Bar(
            x=months,
            y=cumulative_saved,
            name=" Cumulative Saved",
            marker_color="rgba(59, 130, 246, 0.4)",
        )
    )
    fig.update_layout(
        title={"text": "12-Month Financial Trajectory", "font": {"color": "white"}},
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=_FONT,
        height=380,
        margin={"l": 20, "r": 20, "b": 20, "t": 50},
        yaxis_title="Cumulative INR",
        barmode="overlay",
        legend={"orientation": "h", "y": -0.15},
    )
    fig.update_yaxes(gridcolor=_GRID)
    return fig


def create_history_chart(history_df: "pd.DataFrame") -> go.Figure:
    """Create the confession history scatter + 7-day moving average chart.

    Args:
        history_df: DataFrame with columns ``timestamp`` and ``daily_carbon_kg``.

    Returns:
        A Plotly Figure.
    """
    history_df["7_day_MA"] = (
        history_df["daily_carbon_kg"].rolling(window=7, min_periods=1).mean()
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history_df["timestamp"],
            y=history_df["daily_carbon_kg"],
            mode="markers",
            name="Each Confession",
            marker={"color": "#ff4b4b", "size": 8, "opacity": 0.7},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=history_df["timestamp"],
            y=history_df["7_day_MA"],
            mode="lines",
            name="7-Day Trend",
            line={"color": "#ffd700", "width": 3},
        )
    )

    fig.add_hline(
        y=30000 / 365,
        line_dash="dash",
        line_color="red",
        annotation_text=" Category 3",
    )
    fig.add_hline(
        y=15000 / 365,
        line_dash="dash",
        line_color="orange",
        annotation_text=" Category 2",
    )
    fig.add_hline(
        y=9000 / 365,
        line_dash="dash",
        line_color="yellow",
        annotation_text="Category 1",
    )

    fig.update_layout(
        paper_bgcolor=_BG,
        plot_bgcolor=_BG,
        font=_FONT,
        height=400,
        margin={"l": 20, "r": 20, "b": 20, "t": 50},
        xaxis_title="Date",
        yaxis_title="Daily Carbon (kg)",
        legend={"orientation": "h", "y": -0.15},
    )
    fig.update_yaxes(gridcolor=_GRID)
    return fig
