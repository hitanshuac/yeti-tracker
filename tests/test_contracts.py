import pytest
from pydantic import ValidationError

from src.llm_service import ParsedPersonalData


def test_parsed_personal_data_contract():
    """Verify the Pydantic schema validation for LLM output."""
    # Valid input
    valid_data = {"miles_driven": 20, "flight_miles": 0, "transit_miles": 0, "ac_hours": 5, "restaurant_meals": 1}
    validated = ParsedPersonalData(**valid_data)
    assert validated.miles_driven == 20
    assert validated.restaurant_meals == 1

    # Partial fields should use defaults (ge=0, default=0)
    partial = ParsedPersonalData(miles_driven=20)
    assert partial.miles_driven == 20
    assert partial.flight_miles == 0
    assert partial.ac_hours == 0

    # Negative values should raise ValidationError (ge=0 constraint)
    with pytest.raises(ValidationError):
        ParsedPersonalData(miles_driven=-5)

    # Invalid types should raise ValidationError
    with pytest.raises(ValidationError):
        ParsedPersonalData(miles_driven="twenty", flight_miles=0, transit_miles=0, ac_hours=5, restaurant_meals=1)
