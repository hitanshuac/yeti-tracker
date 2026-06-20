import pandas as pd
import plotly.graph_objects as go

from src.chart_factory import (
    create_doom_vs_rescue,
    create_gauge_chart,
    create_history_chart,
    create_savings_waterfall,
)


def test_create_gauge_chart():
    """Verify gauge chart generation."""
    fig = create_gauge_chart(value=5000, max_value=10000, title="Test Gauge")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "indicator"
    assert fig.data[0].value == 5000


def test_create_savings_waterfall():
    """Verify waterfall chart generation with valid savings."""
    fig = create_savings_waterfall(monthly_tax=10000, savings=2000)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
    assert fig.data[0].type == "waterfall"
    assert fig.data[0].y == (10000, -2000, 8000)


def test_create_savings_waterfall_zero_savings():
    """Verify waterfall chart generation gracefully handles zero savings without div-by-zero."""
    fig = create_savings_waterfall(monthly_tax=10000, savings=0)
    assert isinstance(fig, go.Figure)
    assert fig.data[0].y == (10000, 0, 10000)

    # Test zero tax as well
    fig_zero = create_savings_waterfall(monthly_tax=0, savings=0)
    assert isinstance(fig_zero, go.Figure)
    assert fig_zero.data[0].y == (0, 0, 0)


def test_create_doom_vs_rescue():
    """Verify the 12-month projection chart builds successfully."""
    fig = create_doom_vs_rescue(monthly_tax=1000, savings=200)
    assert isinstance(fig, go.Figure)

    # Expecting 3 traces: Doom scatter, Rescue scatter, Cumulative bar
    assert len(fig.data) == 3

    # Doom
    assert fig.data[0].type == "scatter"
    assert fig.data[0].y == (1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000)

    # Rescue (monthly is 800)
    assert fig.data[1].type == "scatter"
    assert fig.data[1].y == (800, 1600, 2400, 3200, 4000, 4800, 5600, 6400, 7200, 8000, 8800, 9600)


def test_create_history_chart():
    """Verify the history scatter+line chart builds with 7-day MA."""
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=10),
            "daily_carbon_kg": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        }
    )

    fig = create_history_chart(df)
    assert isinstance(fig, go.Figure)

    # 2 main traces (scatter for daily, line for MA)
    # The thresholds add_hline creates shape/annotation layouts, not data traces
    assert len(fig.data) == 2

    assert fig.data[0].name == "Each Confession"
    assert fig.data[1].name == "7-Day Trend"
