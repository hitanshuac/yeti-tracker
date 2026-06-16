import os

from app import parse_messy_text, run_duckdb_math


def test_run_duckdb_math():
    """Verify DuckDB logic returns correct carbon and offset trees."""
    # Test high footprint
    carbon, trees = run_duckdb_math(miles=100, ac_hours=10, steaks=2)
    assert carbon > 0
    assert trees > 0

    # Test zero footprint
    carbon, trees = run_duckdb_math(miles=0, ac_hours=0, steaks=0)
    assert carbon == 0.0
    assert trees == 0


def test_parse_messy_text_fallback():
    """Verify that the LLM translator safely falls back if no API key is present."""
    # Temporarily remove API key if it exists
    original_key = os.environ.get("GROQ_API_KEY")
    if original_key:
        del os.environ["GROQ_API_KEY"]

    result = parse_messy_text("I drove 20 miles today")
    assert result["miles_driven"] == 20
    assert result["ac_hours"] == 5
    assert result["steaks_eaten"] == 0

    # Restore API key
    if original_key:
        os.environ["GROQ_API_KEY"] = original_key
