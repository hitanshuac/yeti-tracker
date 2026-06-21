"""
Unit tests for the deterministic carbon math engine.

Tests run_duckdb_math(), classify_tier(), and _calculate_worst_habit()
with isolated DuckDB connections and the production carbon_factors CSV.
"""

from src.carbon_engine import (
    CarbonResult,
    TierClassification,
    classify_tier,
    run_duckdb_math,
)


# ---------------------------------------------------------------------------
# run_duckdb_math tests
# ---------------------------------------------------------------------------


class TestRunDuckdbMath:
    """Tests for the core carbon calculation engine."""

    def test_zero_inputs_returns_baseline(self) -> None:
        """With all zeros, the result should equal the baseline of 2500 kg."""
        result = run_duckdb_math(0, 0, 0, 0, 0, 0, 0, 0)
        assert isinstance(result, CarbonResult)
        assert result.yearly_co2_kg == 2500.0
        assert result.carbon_tax_inr == 2500.0 * 15.80

    def test_car_km_increases_footprint(self) -> None:
        """Adding car_km should increase the yearly CO2 above baseline."""
        result = run_duckdb_math(10000, 0, 0, 0, 0, 0, 0, 0)
        assert result.yearly_co2_kg > 2500.0

    def test_flight_km_increases_footprint(self) -> None:
        """Adding flight_km should increase the yearly CO2 above baseline."""
        result = run_duckdb_math(0, 0, 0, 50000, 0, 0, 0, 0)
        assert result.yearly_co2_kg > 2500.0

    def test_ac_hours_increases_footprint(self) -> None:
        """Adding AC hours should increase the yearly CO2 above baseline."""
        result = run_duckdb_math(0, 0, 0, 0, 0, 0, 12, 0)
        assert result.yearly_co2_kg > 2500.0

    def test_restaurant_meals_increases_footprint(self) -> None:
        """Adding restaurant meals should increase the yearly CO2."""
        result = run_duckdb_math(0, 0, 0, 0, 0, 0, 0, 365)
        assert result.yearly_co2_kg > 2500.0

    def test_breakdown_contains_expected_keys(self) -> None:
        """The breakdown dict should contain all expected category keys."""
        result = run_duckdb_math(100, 100, 100, 100, 100, 100, 4, 100)
        assert " Basic Living (Home Meals, Shelter, Grid)" in result.breakdown
        assert " Car & Transit" in result.breakdown
        assert " Flights" in result.breakdown
        assert " AC / Heating" in result.breakdown
        assert " Dining Out (Above Home Cooking)" in result.breakdown

    def test_worst_habit_identified(self) -> None:
        """With high flight_km, the worst habit should be Flights."""
        result = run_duckdb_math(0, 0, 0, 100000, 0, 0, 0, 0)
        assert "Flights" in result.worst_habit

    def test_result_is_validated_pydantic_model(self) -> None:
        """The result must be a validated Pydantic CarbonResult model."""
        result = run_duckdb_math(0, 0, 0, 0, 0, 0, 0, 0)
        assert isinstance(result, CarbonResult)
        assert result.yearly_co2_kg >= 0
        assert result.carbon_tax_inr >= 0

    def test_missing_csv_returns_baseline_gracefully(self) -> None:
        """With a missing CSV, factors default to hardcoded values."""
        result = run_duckdb_math(
            100,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            dataset_path="nonexistent_path.csv",
        )
        # Should still return a valid result (with default factor fallbacks)
        assert isinstance(result, CarbonResult)
        assert result.yearly_co2_kg >= 2500.0


# ---------------------------------------------------------------------------
# classify_tier tests
# ---------------------------------------------------------------------------


class TestClassifyTier:
    """Tests for gamification tier classification."""

    def test_human_tier(self) -> None:
        """Yearly CO2 <= 9000 should be 'Human' tier."""
        tier = classify_tier(5000)
        assert isinstance(tier, TierClassification)
        assert tier.tier == "Human"
        assert tier.color == "#00cc66"

    def test_category_1_warning(self) -> None:
        """Yearly CO2 between 9001-15000 should be 'Category 1 Warning'."""
        tier = classify_tier(12000)
        assert tier.tier == "Category 1 Warning"
        assert tier.color == "#ffd700"

    def test_category_2_catastrophe(self) -> None:
        """Yearly CO2 between 15001-30000 should be 'Category 2 Catastrophe'."""
        tier = classify_tier(20000)
        assert tier.tier == "Category 2 Catastrophe"
        assert tier.color == "#ffaa00"

    def test_category_3_catastrophe(self) -> None:
        """Yearly CO2 > 30000 should be 'Category 3 Catastrophe'."""
        tier = classify_tier(50000)
        assert tier.tier == "Category 3 Catastrophe"
        assert tier.color == "#ff4b4b"

    def test_boundary_9000_is_human(self) -> None:
        """Exactly 9000 kg should still be Human tier."""
        tier = classify_tier(9000)
        assert tier.tier == "Human"

    def test_boundary_9001_is_cat1(self) -> None:
        """9001 kg should trigger Category 1 Warning."""
        tier = classify_tier(9001)
        assert tier.tier == "Category 1 Warning"

    def test_boundary_30001_is_cat3(self) -> None:
        """30001 kg should trigger Category 3 Catastrophe."""
        tier = classify_tier(30001)
        assert tier.tier == "Category 3 Catastrophe"

    def test_zero_co2_is_human(self) -> None:
        """Zero CO2 should classify as Human."""
        tier = classify_tier(0)
        assert tier.tier == "Human"

    def test_tier_has_image_path(self) -> None:
        """All tiers should have an image_path defined."""
        for co2 in [2500, 12000, 20000, 50000]:
            tier = classify_tier(co2)
            assert tier.image_path is not None
