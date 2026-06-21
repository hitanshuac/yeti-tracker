"""
# pylint: disable=line-too-long,broad-exception-caught,unused-argument
Pydantic response schemas (enforced, not decorative).
"""

import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ParsedPersonalData(BaseModel):
    """Schema for parsed lifestyle activities from natural language."""

    reasoning: str = ""
    is_valid: bool = True
    rejection_reason: str = ""
    car_km: int = Field(ge=0, default=0)
    two_wheeler_km: int = Field(ge=0, default=0)
    auto_rickshaw_km: int = Field(ge=0, default=0)
    flight_km: int = Field(ge=0, default=0)
    bus_km: int = Field(ge=0, default=0)
    train_metro_km: int = Field(ge=0, default=0)
    ac_hours: int = Field(ge=0, default=0)
    restaurant_meals: int = Field(ge=0, default=0)
    untracked_activities: list[str] = Field(
        default_factory=list,
        description="Any high-carbon activities mentioned that don't fit the exact metrics above (e.g., eating beef, helicopter rides).",
    )

    @field_validator("*", mode="before")
    @classmethod
    def _eval_math(cls, v: Any) -> Any:
        if isinstance(v, str) and re.fullmatch(r"[\d\s\*\+\-\/\.]+", v):
            try:
                # pylint: disable=eval-used
                return int(float(eval(v)))
            except Exception:
                pass
        return v


class AdvisorAlternative(BaseModel):
    """A single reduction strategy alternative."""

    type: str
    alternative: str
    pros: str
    cons: str
    est_monthly_savings_inr: float


class AdvisorResponse(BaseModel):
    """Typed schema for the Yeti Advisor output."""

    analysis: str = "System Override: No analysis provided."
    silver_lining: str = "You're being honest about your habits  that's the first step."
    roast: str = "But let's see if we can do better, shall we?"
    guilt_easing_question: str = (
        "Tell me more about your daily routine  any hidden habits?"
    )
    alternatives: list[AdvisorAlternative] = Field(
        default_factory=lambda: [
            AdvisorAlternative(
                type="Convenience",
                alternative="Switch to public transit for short trips",
                pros="Saves money and reduces emissions",
                cons="Less flexibility in schedule",
                est_monthly_savings_inr=400.0,
            ),
            AdvisorAlternative(
                type="Maximum Impact",
                alternative="Replace AC with a ceiling fan when temperature permits",
                pros="Massive electricity and carbon savings",
                cons="Less comfortable on very hot days",
                est_monthly_savings_inr=1500.0,
            ),
        ]
    )


class AdvisorRequest(BaseModel):
    """Encapsulates the request payload to the Advisor LLM."""

    carbon: float
    tax: float
    car_km: int
    two_wheeler_km: int
    auto_rickshaw_km: int
    flight_km: int
    bus_km: int
    train_metro_km: int
    ac_hours: int
    restaurant_meals: int
    tier: str
    goal: str
    kpis: str
    worst_habit: str
    rag_context: str = ""
    raw_text: str = ""
