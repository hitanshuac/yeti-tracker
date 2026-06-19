"""
Centralized session state management for the Yeti-Tracker UI.

Replaces the flat st.session_state key-value bag with a typed Pydantic model
that syncs bidirectionally with Streamlit's session_state.
"""

import uuid

from pydantic import BaseModel, Field


class AppState(BaseModel):
    """Single source of truth for all UI state.

    Every key that app.py previously scattered across st.session_state
    is now a typed, validated field.
    """

    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Slider values (yearly integers)
    car_miles: int = 0
    flight_miles: int = 0
    transit_miles: int = 0
    ac_hours: int = 0
    restaurant_meals: int = 0

    # Confessional text
    confessional_input: str = (
        "I drove about 40 miles round trip for work. "
        "Ate out at a fancy restaurant for lunch. "
        "Left the AC on for 10 hours."
    )
    last_extracted_text: str = ""

    # Control flags
    has_calculated: bool = False
    run_math: bool = False
    auto_extracted: bool = False
    show_rescue: bool = False
    history_seeded: bool = False


# ---------------------------------------------------------------------------
# Session-state synchronization helpers
# ---------------------------------------------------------------------------

_STATE_KEY = "_app_state_initialized"


def init_state(st_session_state: dict) -> None:
    """Initialize st.session_state with default AppState values.

    Only runs once per session.  Individual keys are written into
    st.session_state so Streamlit widgets (which bind via ``key=``)
    continue to work unchanged.

    Args:
        st_session_state: The ``st.session_state`` proxy dict.
    """
    if _STATE_KEY in st_session_state:
        return

    defaults = AppState()
    for field_name, value in defaults.model_dump().items():
        if field_name not in st_session_state:
            st_session_state[field_name] = value

    # Sync last_extracted_text to confessional default
    if "last_extracted_text" not in st_session_state or not st_session_state["last_extracted_text"]:
        st_session_state["last_extracted_text"] = st_session_state["confessional_input"]

    st_session_state[_STATE_KEY] = True


def get_state(st_session_state: dict) -> AppState:
    """Snapshot the live st.session_state into a validated AppState.

    Args:
        st_session_state: The ``st.session_state`` proxy dict.

    Returns:
        A validated AppState instance reflecting the current session.
    """
    fields = AppState.model_fields.keys()
    data = {k: st_session_state[k] for k in fields if k in st_session_state}
    return AppState(**data)
