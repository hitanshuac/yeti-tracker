import pytest
from pydantic import ValidationError

from app import ParsedPersonalData


def test_parsed_personal_data_contract():
    """Verify the Pydantic schema validation for LLM output."""
    # Valid input
    valid_data = {"miles_driven": 20, "ac_hours": 5, "steaks_eaten": 1}
    validated = ParsedPersonalData(**valid_data)
    assert validated.miles_driven == 20

    # Missing fields should raise ValidationError
    with pytest.raises(ValidationError):
        ParsedPersonalData(miles_driven=20)  # Missing others

    # Invalid types should raise ValidationError
    with pytest.raises(ValidationError):
        ParsedPersonalData(miles_driven="twenty", ac_hours=5, steaks_eaten=1)
