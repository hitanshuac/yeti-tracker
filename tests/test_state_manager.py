from src.state_manager import AppState, get_state, init_state


def test_init_state_empty():
    """Verify init_state populates defaults safely."""
    st_mock = {}
    init_state(st_mock)

    # Assert defaults were written
    assert "_app_state_initialized" in st_mock
    assert st_mock["car_km"] == 0
    assert st_mock["daily_sleep_hours"] == 8

    # Assert session_id was generated
    assert "session_id" in st_mock
    assert len(st_mock["session_id"]) > 0


def test_init_state_existing():
    """Verify init_state does not overwrite existing keys."""
    st_mock = {"car_km": 500, "session_id": "mock-uuid"}
    init_state(st_mock)

    # Existing fields must be preserved
    assert st_mock["car_km"] == 500
    assert st_mock["session_id"] == "mock-uuid"

    # Missing fields must be populated
    assert st_mock["flight_km"] == 0
    assert "_app_state_initialized" in st_mock


def test_get_state():
    """Verify get_state returns a validated AppState from dict."""
    st_mock = {
        "car_km": 500,
        "flight_km": 1000,
        "transit_km": 0,
        "daily_sleep_hours": 7,
        "sleep_ac_on": True,
        "daytime_ac_hours": 4,
        "restaurant_meals": 10,
        "session_id": "test-id",
    }

    # init_state populates missing fields to satisfy the Pydantic schema
    init_state(st_mock)

    state = get_state(st_mock)
    assert isinstance(state, AppState)
    assert state.car_km == 500
    assert state.sleep_ac_on is True
    assert state.session_id == "test-id"
