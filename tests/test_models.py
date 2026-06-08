import pytest
from datetime import datetime
from uuid import UUID

from src.models.carbon_activity import CarbonActivity

def test_carbon_activity_valid():
    activity = CarbonActivity(
        activity_id="123e4567-e89b-12d3-a456-426614174000",
        user_id="user_123",
        activity_type="transport",
        carbon_kg=12.5,
        timestamp=datetime.now()
    )
    assert isinstance(activity.activity_id, UUID)
    assert activity.carbon_kg == 12.5

def test_carbon_activity_negative_carbon():
    with pytest.raises(ValueError):
        CarbonActivity(
            activity_id="123e4567-e89b-12d3-a456-426614174000",
            user_id="user_123",
            activity_type="transport",
            carbon_kg=-5.0,
            timestamp=datetime.now()
        )
