"""
Deterministic carbon math engine using DuckDB.

All financial and CO2 calculations live here — no LLM, no UI.
The engine reads emission factors from a CSV and returns typed results.
"""

import json
import os

import duckdb
from pydantic import BaseModel, Field


class CarbonResult(BaseModel):
    """Typed return value from the carbon calculation engine."""

    yearly_co2_kg: float = Field(ge=0)
    carbon_tax_inr: float = Field(ge=0)
    breakdown: dict[str, float] = Field(default_factory=dict)


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
        query = f"SELECT activity, co2_kg_per_unit, social_cost_usd_per_kg " f"FROM read_csv_auto('{dataset_path}')"
        results = conn.execute(query).fetchall()
        return {row[0]: {"co2": float(row[1]), "scc": float(row[2])} for row in results}
    except Exception as e:
        _log_engine_error(e)
        return {}
    finally:
        conn.close()


def run_duckdb_math(
    car_miles: int,
    flight_miles: int,
    transit_miles: int,
    ac_hours: int,
    restaurant_meals: int,
    dataset_path: str = "data/carbon_factors.csv",
) -> CarbonResult:
    """Calculate forecasted carbon footprint and financial cost using DuckDB.

    Args:
        car_miles: Yearly car kilometers.
        flight_miles: Yearly flight kilometers.
        transit_miles: Yearly public transit kilometers.
        ac_hours: Yearly AC/heating hours.
        restaurant_meals: Yearly restaurant meals.
        dataset_path: Path to the emission factors CSV.

    Returns:
        A validated CarbonResult with yearly CO2, tax, and breakdown.
    """
    factors = _load_factors(dataset_path)

    def _get(activity: str, key: str, default: float) -> float:
        return factors.get(activity, {}).get(key, default)

    yearly_car_co2 = car_miles * _get("miles_driven", "co2", 0.4)
    yearly_flight_co2 = flight_miles * _get("flight_miles", "co2", 0.25)
    yearly_transit_co2 = transit_miles * _get("transit_miles", "co2", 0.14)
    yearly_ac_co2 = ac_hours * _get("ac_hours", "co2", 1.5)
    yearly_restaurant_co2 = restaurant_meals * _get("restaurant_meal", "co2", 8.5)

    yearly_transport = yearly_car_co2 + yearly_flight_co2 + yearly_transit_co2
    yearly_ac = yearly_ac_co2
    yearly_restaurant = yearly_restaurant_co2

    yearly_co2 = yearly_transport + yearly_ac + yearly_restaurant

    carbon_tax = (
        yearly_transport * _get("miles_driven", "scc", 0.19)
        + yearly_ac * _get("ac_hours", "scc", 0.19)
        + yearly_restaurant * _get("restaurant_meal", "scc", 2.50)
    )

    breakdown = {
        "Transportation": yearly_transport,
        "AC/Heating": yearly_ac,
        "Eating Out": yearly_restaurant,
    }

    return CarbonResult(
        yearly_co2_kg=yearly_co2,
        carbon_tax_inr=carbon_tax,
        breakdown=breakdown,
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
            image_path="data/assets/godzilla.jpg",
        )
    if yearly_co2 > 15000:
        return TierClassification(
            tier="Category 2 Catastrophe",
            color="#ffaa00",
            message=f"CATEGORY 2 CATASTROPHE ({monthly:,.0f} kg / mo)",
            image_path="data/assets/yeti.jpg",
        )
    if yearly_co2 > 9000:
        return TierClassification(
            tier="Category 1 Warning",
            color="#ffd700",
            message=f"CATEGORY 1 WARNING ({monthly:,.0f} kg / mo)",
            image_path="data/assets/vegeta.jpg",
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
