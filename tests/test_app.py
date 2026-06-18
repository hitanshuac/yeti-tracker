import os

from app import fetch_rag_context, parse_messy_text, run_duckdb_math

FIXTURE_PATH = "tests/fixtures/carbon_factors_fixture.csv"


def test_run_duckdb_math():
    """Verify DuckDB logic returns correct carbon and offset trees."""
    carbon, tax, _ = run_duckdb_math(
        car_miles=100, flight_miles=500, transit_miles=50, ac_hours=10, restaurant_meals=2, dataset_path=FIXTURE_PATH
    )
    assert carbon > 0
    assert tax > 0

    carbon, tax, _ = run_duckdb_math(
        car_miles=0, flight_miles=0, transit_miles=0, ac_hours=0, restaurant_meals=0, dataset_path=FIXTURE_PATH
    )
    assert carbon == 0.0
    assert tax == 0.0


def test_parse_messy_text_fallback():
    """Verify that the LLM translator safely falls back if no API key is present."""
    original_key = os.environ.get("GROQ_API_KEY")
    if original_key:
        del os.environ["GROQ_API_KEY"]

    result = parse_messy_text("I drove 20 miles today")
    assert result["miles_driven"] == 0
    assert result["ac_hours"] == 0
    assert result["restaurant_meals"] == 0

    if original_key:
        os.environ["GROQ_API_KEY"] = original_key


def test_fetch_rag_context():
    """Verify DuckDB FTS context retrieval using isolated fixtures."""
    context = fetch_rag_context("I drank bottled water today", dataset_path=FIXTURE_PATH)
    assert "bottled_water_liter" in context
    assert "0.15" in context

    context_mock = fetch_rag_context("I need to test my mock keyword", dataset_path=FIXTURE_PATH)
    assert "mock_keyword_test" in context_mock
