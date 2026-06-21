"""
# pylint: disable=line-too-long
Deterministic carbon math engine using DuckDB.

All financial and CO2 calculations live here  no LLM, no UI.
The engine reads emission factors from a CSV and returns typed results.
"""

import duckdb
from pydantic import BaseModel, Field

from src.observability import log_error


class CarbonResult(BaseModel):
    """Typed return value from the carbon calculation engine."""

    yearly_co2_kg: float = Field(ge=0)
    carbon_tax_inr: float = Field(ge=0)
    breakdown: dict[str, float] = Field(default_factory=dict)
    is_anomaly: bool = Field(default=False)
    worst_habit: str = Field(default="")


class TierClassification(BaseModel):
    """Gamification tier based on yearly CO2 output."""

    tier: str
    color: str
    message: str
    image_path: str | None = None


# ---------------------------------------------------------------------------
# Core math
# ---------------------------------------------------------------------------


def _load_factors(dataset_path: str) -> dict[str, dict[str, float]]:
    """Load CO2 factors from CSV via DuckDB.

    Args:
        dataset_path: Path to the carbon_factors CSV.

    Returns:
        Dict mapping activity -> {"co2": float, "scc": float}.
    """
    conn = duckdb.connect()
    try:
        query = f"SELECT activity, co2_kg_per_unit, social_cost_inr_per_kg FROM read_csv_auto('{dataset_path}')"
        results = conn.execute(query).fetchall()
        return {row[0]: {"co2": float(row[1]), "scc": float(row[2])} for row in results}
    except duckdb.Error as e:
        log_error(type(e).__name__, "carbon_engine", str(e))
        return {}
    finally:
        conn.close()


def _detect_anomaly(
    session_id: str, daily_co2_kg: float, db_path: str = "data/yeti.duckdb"
) -> bool:
    """Detects if the given daily carbon footprint is > 90th percentile of last 30 days using DuckDB."""
    try:
        conn = duckdb.connect(db_path)
        query = """
            SELECT quantile_cont(daily_carbon_kg, 0.90)
            FROM (
                SELECT daily_carbon_kg
                FROM user_history
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT 30
            )
        """
        result = conn.execute(query, [session_id]).fetchone()
        conn.close()

        if result and result[0] is not None:
            p90 = result[0]
            return daily_co2_kg > p90
        return False
    except duckdb.CatalogException:
        return False
    except duckdb.Error as e:
        log_error(type(e).__name__, "carbon_engine", str(e))
        return False


def _calculate_worst_habit(breakdown: dict[str, float]) -> str:
    """Identify the worst discretionary habit from the breakdown."""
    discretionary = {k: v for k, v in breakdown.items() if "Basic Living" not in k}
    return max(discretionary, key=discretionary.get) if discretionary else "Unknown"


def run_duckdb_math(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    car_km: int,
    two_wheeler_km: int,
    auto_rickshaw_km: int,
    flight_km: int,
    bus_km: int,
    train_metro_km: int,
    ac_hours: int,
    restaurant_meals: int,
    dataset_path: str = "data/carbon_factors.csv",
    session_id: str | None = None,
) -> CarbonResult:
    """Calculate forecasted carbon footprint and financial cost using DuckDB.

    Args:
        car_km: Yearly car kilometers.
        two_wheeler_km: Yearly two-wheeler/bike kilometers.
        auto_rickshaw_km: Yearly auto-rickshaw/cab kilometers.
        flight_km: Yearly flight kilometers.
        bus_km: Yearly bus kilometers.
        train_metro_km: Yearly train/metro kilometers.
        ac_hours: Average daily hours of AC/cooler usage.
        restaurant_meals: Yearly restaurant meals.
        dataset_path: Path to the emission factors CSV.
        session_id: Optional session ID for dynamic baseline inference.

    Returns:
        A validated CarbonResult with yearly CO2, tax, and breakdown.
    """
    factors = _load_factors(dataset_path)

    def _get(activity: str, key: str, default: float) -> float:
        return factors.get(activity, {}).get(key, default)

    # World Bank Static Baseline for India: 2500 kg total
    # As requested, keeping the factual 2500 kg without subtracting.
    baseline_footprint_kg = 2500.0
    scc_inr_per_kg = 15.80

    yearly_car_co2 = car_km * _get("car_km", "co2", 0.15)
    yearly_two_wheeler_co2 = two_wheeler_km * _get("two_wheeler_km", "co2", 0.04)
    yearly_auto_rickshaw_co2 = auto_rickshaw_km * _get("auto_rickshaw_km", "co2", 0.08)
    yearly_flight_co2 = flight_km * _get("flight_km", "co2", 0.115)
    yearly_bus_co2 = bus_km * _get("bus_km", "co2", 0.08)
    yearly_train_co2 = train_metro_km * _get("train_km", "co2", 0.01)

    ac_factor = _get("ac_hours", "co2", 1.12)
    yearly_ac = (ac_hours * 365) * ac_factor

    yearly_restaurant_co2 = restaurant_meals * _get("restaurant_meal", "co2", 3.5)

    yearly_transport = (
        yearly_car_co2
        + yearly_two_wheeler_co2
        + yearly_auto_rickshaw_co2
        + yearly_bus_co2
        + yearly_train_co2
    )
    yearly_flight = yearly_flight_co2
    yearly_restaurant = yearly_restaurant_co2

    yearly_co2 = (
        yearly_transport
        + yearly_flight
        + yearly_ac
        + yearly_restaurant
        + baseline_footprint_kg
    )

    is_anomaly = False
    if session_id:
        daily_co2 = yearly_co2 / 365.0
        is_anomaly = _detect_anomaly(session_id, daily_co2)

    carbon_tax = yearly_co2 * scc_inr_per_kg

    breakdown = {
        " Basic Living (Home Meals, Shelter, Grid)": baseline_footprint_kg,
        " Car & Transit": yearly_transport,
        " Flights": yearly_flight,
        " AC / Heating": yearly_ac,
        " Dining Out (Above Home Cooking)": yearly_restaurant,
    }

    worst_habit = _calculate_worst_habit(breakdown)

    return CarbonResult(
        yearly_co2_kg=yearly_co2,
        carbon_tax_inr=carbon_tax,
        breakdown=breakdown,
        is_anomaly=is_anomaly,
        worst_habit=worst_habit,
    )


# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------


def classify_tier(yearly_co2: float) -> TierClassification:
    """Classify the user's yearly CO2 into a gamification tier.

    Args:
        yearly_co2: Total yearly CO2 in kg.

    Returns:
        A TierClassification with tier name, color, display message, and
        optional image path.
    """
    monthly = yearly_co2 / 12.0

    if yearly_co2 > 30000:
        return TierClassification(
            tier="Category 3 Catastrophe",
            color="#ff4b4b",
            message="You didn't just leave a footprint today, you left a crater. The Yeti is obese.",
            image_path="data/assets/tier3.jpg",
        )
    if yearly_co2 > 15000:
        return TierClassification(
            tier="Category 2 Catastrophe",
            color="#ffaa00",
            message=f"CATEGORY 2 CATASTROPHE ({monthly:,.0f} kg / mo)",
            image_path="data/assets/tier2.jpg",
        )
    if yearly_co2 > 9000:
        return TierClassification(
            tier="Category 1 Warning",
            color="#ffd700",
            message=f"CATEGORY 1 WARNING ({monthly:,.0f} kg / mo)",
            image_path="data/assets/tier1.jpg",
        )
    return TierClassification(
        tier="Human",
        color="#00cc66",
        message=f"ACCEPTABLE IMPACT ({monthly:,.0f} kg / mo)",
        image_path="data/assets/tier_human.png",
    )


# ---------------------------------------------------------------------------
# End of file
# ---------------------------------------------------------------------------
