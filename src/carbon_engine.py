"""
Deterministic carbon math engine using DuckDB.

All financial and CO2 calculations live here — no LLM, no UI.
The engine reads emission factors from a CSV and returns typed results.
"""

import json
import os

import duckdb
from pydantic import BaseModel, Field

from src.anomaly_detector import detect_anomaly_and_baseline


class CarbonResult(BaseModel):
    """Typed return value from the carbon calculation engine."""

    yearly_co2_kg: float = Field(ge=0)
    carbon_tax_inr: float = Field(ge=0)
    breakdown: dict[str, float] = Field(default_factory=dict)
    is_anomaly: bool = Field(default=False)


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
        query = f"SELECT activity, co2_kg_per_unit, social_cost_inr_per_kg " f"FROM read_csv_auto('{dataset_path}')"
        results = conn.execute(query).fetchall()
        return {row[0]: {"co2": float(row[1]), "scc": float(row[2])} for row in results}
    except Exception as e:
        _log_engine_error(e)
        return {}
    finally:
        conn.close()


def run_duckdb_math(
    car_km: int,
    flight_km: int,
    transit_km: int,
    ac_hours: int,
    restaurant_meals: int,
    dataset_path: str = "data/carbon_factors.csv",
    session_id: str | None = None,
) -> CarbonResult:
    """Calculate forecasted carbon footprint and financial cost using DuckDB.

    Args:
        car_km: Yearly car kilometers.
        flight_km: Yearly flight kilometers.
        transit_km: Yearly public transit kilometers.
        ac_hours: Yearly AC/heating hours.
        restaurant_meals: Yearly restaurant meals.
        dataset_path: Path to the emission factors CSV.
        session_id: Optional session ID for dynamic baseline inference.

    Returns:
        A validated CarbonResult with yearly CO2, tax, and breakdown.
    """
    factors = _load_factors(dataset_path)

    def _get(activity: str, key: str, default: float) -> float:
        return factors.get(activity, {}).get(key, default)

    if session_id:
        baseline_kg, is_anomaly = detect_anomaly_and_baseline(session_id)
    else:
        baseline_kg, is_anomaly = 1500.0, False

    BASELINE_FOOTPRINT_KG = baseline_kg
    SCC_INR_PER_KG = 15.80

    yearly_car_co2 = car_km * _get("car_km", "co2", 0.15)
    yearly_flight_co2 = flight_km * _get("flight_km", "co2", 0.115)
    yearly_transit_co2 = transit_km * _get("train_km", "co2", 0.01)
    yearly_ac_co2 = ac_hours * _get("ac_hours", "co2", 1.12)
    yearly_restaurant_co2 = restaurant_meals * _get("restaurant_meal", "co2", 3.5)

    yearly_transport = yearly_car_co2 + yearly_flight_co2 + yearly_transit_co2
    yearly_ac = yearly_ac_co2
    yearly_restaurant = yearly_restaurant_co2

    yearly_co2 = yearly_transport + yearly_ac + yearly_restaurant + BASELINE_FOOTPRINT_KG

    carbon_tax = yearly_co2 * SCC_INR_PER_KG

    breakdown = {
        "🏠 Basic Living (Home Meals, Shelter, Grid)": BASELINE_FOOTPRINT_KG,
        "🚗 Car, Flights & Transit": yearly_transport,
        "❄️ AC / Heating": yearly_ac,
        "🍽️ Dining Out (Above Home Cooking)": yearly_restaurant,
    }

    return CarbonResult(
        yearly_co2_kg=yearly_co2,
        carbon_tax_inr=carbon_tax,
        breakdown=breakdown,
        is_anomaly=is_anomaly,
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
            message=f"CATEGORY 3 CATASTROPHE ({monthly:,.0f} kg / mo)",
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
        image_path=None,
    )


# ---------------------------------------------------------------------------
# Internal error logging (avoids circular import with observability)
# ---------------------------------------------------------------------------


def _log_engine_error(error: Exception) -> None:
    """Minimal error logger to avoid coupling to the UI layer."""
    log_file = "data/error_logs.json"
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    try:
        with open(log_file, encoding="utf-8") as f:
            logs = json.load(f)
            if not isinstance(logs, list):
                logs = []
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []

    logs.append(
        {
            "error_type": type(error).__name__,
            "component": "carbon_engine",
            "message": str(error),
            "status": "UNRESOLVED",
            "resolution_strategy": None,
        }
    )

    temp_file = f"{log_file}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    os.replace(temp_file, log_file)
