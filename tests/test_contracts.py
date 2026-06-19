import pytest
from pydantic import ValidationError

from src.llm_service import ParsedPersonalData


def test_parsed_personal_data_contract():
    """Verify the Pydantic schema validation for LLM output."""
    # Valid input
    valid_data = {"car_km": 20, "flight_km": 0, "transit_km": 0, "ac_hours": 5, "restaurant_meals": 1}
    validated = ParsedPersonalData(**valid_data)
    assert validated.car_km == 20
    assert validated.restaurant_meals == 1

    # Partial fields should use defaults (ge=0, default=0)
    partial = ParsedPersonalData(car_km=20)
    assert partial.car_km == 20
    assert partial.flight_km == 0
    assert partial.ac_hours == 0

    # Negative values should raise ValidationError (ge=0 constraint)
    with pytest.raises(ValidationError):
        ParsedPersonalData(car_km=-5)

    # Invalid types should raise ValidationError
    with pytest.raises(ValidationError):
        ParsedPersonalData(car_km="twenty", flight_km=0, transit_km=0, ac_hours=5, restaurant_meals=1)
