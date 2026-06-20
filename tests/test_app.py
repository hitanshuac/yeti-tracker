"""Tests for the Yeti-Tracker core modules."""

import os

from src.carbon_engine import run_duckdb_math
from src.llm_service import parse_confession
from src.rag_service import fetch_rag_context

FIXTURE_PATH = "tests/fixtures/carbon_factors_fixture.csv"


def test_run_duckdb_math():
    """Verify DuckDB logic returns correct carbon and tax values."""
    result = run_duckdb_math(
        car_km=100,
        flight_km=500,
        transit_km=50,
        daily_sleep_hours=8,
        sleep_ac_on=True,
        daytime_ac_hours=2,
        restaurant_meals=2,
        dataset_path=FIXTURE_PATH,
    )
    assert result.yearly_co2_kg > 0
    assert result.carbon_tax_inr > 0

    result_zero = run_duckdb_math(
        car_km=0,
        flight_km=0,
        transit_km=0,
        daily_sleep_hours=8,
        sleep_ac_on=False,
        daytime_ac_hours=0,
        restaurant_meals=0,
        dataset_path=FIXTURE_PATH,
    )
    # With 0 lifestyle inputs, only the 2500 kg baseline should remain
    assert result_zero.yearly_co2_kg == 2500.0
    assert result_zero.carbon_tax_inr == 2500.0 * 15.80


def test_parse_confession_fallback():
    """Verify that the LLM translator safely falls back if no API key is present."""
    original_key = os.environ.get("GROQ_API_KEY")
    if original_key:
        del os.environ["GROQ_API_KEY"]

    result = parse_confession("I drove 20 km today")
    assert result.car_km == 0
    assert result.daily_sleep_hours == 8
    assert result.sleep_ac_on is False
    assert result.restaurant_meals == 0

    if original_key:
        os.environ["GROQ_API_KEY"] = original_key


def test_fetch_rag_context():
    """Verify DuckDB FTS context retrieval using isolated fixtures."""
    context = fetch_rag_context("I drank bottled water today", dataset_path=FIXTURE_PATH)
    assert "bottled_water_liter" in context
    assert "0.15" in context

    context_mock = fetch_rag_context("I need to test my mock keyword", dataset_path=FIXTURE_PATH)
    assert "mock_keyword_test" in context_mock
