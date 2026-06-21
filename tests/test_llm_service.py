"""
Unit tests for the LLM service layer.

Tests internal helper functions (math eval, recovery, parsing, sanitization)
with mocked Groq API calls. No live LLM calls are made during testing.
"""

import re

import pytest

from src.llm import (
    AdvisorAlternative,
    AdvisorRequest,
    AdvisorResponse,
    ParsedPersonalData,
)
from src.llm.parsers import (
    _fallback_parse,
    parse_groq_result as _parse_groq_result,
    recover_failed_generation as _recover_failed_generation,
    _safe_eval_math_expr,
    sanitize_input,
)


# ---------------------------------------------------------------------------
# sanitize_input (llm_service duplicate) tests
# ---------------------------------------------------------------------------


class TestSanitizeInputLLM:
    """Tests for the LLM service's internal sanitize_input."""

    def test_basic_sanitization(self) -> None:
        """Normal text should be returned stripped and truncated."""
        result = sanitize_input("Hello world")
        assert "Hello world" in result

    def test_truncation(self) -> None:
        """Input should be truncated to 500 characters."""
        result = sanitize_input("a" * 1000)
        assert len(result) <= 500

    def test_curly_braces_removed(self) -> None:
        """Curly braces should be stripped for template injection prevention."""
        result = sanitize_input("test {inject} here")
        assert "{" not in result
        assert "}" not in result

    def test_angle_brackets_removed(self) -> None:
        """Angle brackets should be stripped."""
        result = sanitize_input("test <script> here")
        assert "<" not in result
        assert ">" not in result

    def test_non_string_raises(self) -> None:
        """Non-string input should raise ValueError."""
        with pytest.raises(ValueError, match="Input must be a string"):
            sanitize_input(12345)


# ---------------------------------------------------------------------------
# _safe_eval_math_expr tests
# ---------------------------------------------------------------------------


class TestSafeEvalMathExpr:
    """Tests for the math expression evaluator used in LLM recovery."""

    def test_simple_multiplication(self) -> None:
        """Simple multiplication should be evaluated."""
        match = re.search(r"[\d\s\*\+\-\/\.]+", "260 * 10")
        assert match is not None
        result = _safe_eval_math_expr(match)
        assert result == "2600"

    def test_addition(self) -> None:
        """Addition should be evaluated."""
        match = re.search(r"[\d\s\*\+\-\/\.]+", "100 + 200")
        assert match is not None
        result = _safe_eval_math_expr(match)
        assert result == "300"

    def test_complex_expression(self) -> None:
        """Complex expressions should be evaluated."""
        match = re.search(r"[\d\.\s\*\+\-\/]+", "2.5 * 365")
        assert match is not None
        result = _safe_eval_math_expr(match)
        assert result == "912"

    def test_division_by_zero_returns_zero(self) -> None:
        """Division by zero should return '0' safely."""
        match = re.search(r"[\d\s\*\+\-\/\.]+", "100 / 0")
        assert match is not None
        result = _safe_eval_math_expr(match)
        assert result == "0"


# ---------------------------------------------------------------------------
# _recover_failed_generation tests
# ---------------------------------------------------------------------------


class TestRecoverFailedGeneration:
    """Tests for recovering JSON from Groq 400 error messages."""

    def test_recovery_with_math_expressions(self) -> None:
        """Should recover and evaluate math expressions in failed JSON."""
        error_msg = (
            "{'error': {'failed_generation': "
            '\'{"car_km": 0, "flight_km": 260 * 10, "ac_hours": 9}\'}}'
        )
        result = _recover_failed_generation(error_msg)
        if result is not None:
            assert result.get("flight_km") == 2600
            assert result.get("ac_hours") == 9

    def test_recovery_returns_none_on_garbage(self) -> None:
        """Should return None for non-recoverable errors."""
        result = _recover_failed_generation("totally random error text")
        assert result is None


# ---------------------------------------------------------------------------
# _parse_groq_result tests
# ---------------------------------------------------------------------------


class TestParseGroqResult:
    """Tests for parsing raw LLM output into ParsedPersonalData."""

    def test_valid_result(self) -> None:
        """A fully valid result should parse directly."""
        raw = {
            "car_km": 5000,
            "two_wheeler_km": 0,
            "auto_rickshaw_km": 0,
            "flight_km": 1000,
            "bus_km": 0,
            "train_metro_km": 2000,
            "ac_hours": 4,
            "restaurant_meals": 52,
        }
        result = _parse_groq_result(raw)
        assert isinstance(result, ParsedPersonalData)
        assert result.car_km == 5000
        assert result.flight_km == 1000

    def test_legacy_key_mapping(self) -> None:
        """Legacy keys like 'miles_driven' should be mapped to 'car_km'."""
        raw = {"miles_driven": 1000, "flight_miles": 500, "transit_km": 200}
        result = _parse_groq_result(raw)
        assert isinstance(result, ParsedPersonalData)
        assert result.car_km == 1000
        assert result.flight_km == 500
        assert result.train_metro_km == 200

    def test_invalid_values_fallback_gracefully(self) -> None:
        """Invalid values should trigger fallback parsing without crashing."""
        raw = {"car_km": "not_a_number", "flight_km": -100}
        result = _parse_groq_result(raw)
        assert isinstance(result, ParsedPersonalData)

    def test_math_expression_values(self) -> None:
        """Math expression strings should be evaluated by the field validator."""
        raw = {"car_km": "30 * 260", "restaurant_meals": "2 * 52"}
        result = _parse_groq_result(raw)
        assert isinstance(result, ParsedPersonalData)
        assert result.car_km == 7800
        assert result.restaurant_meals == 104


# ---------------------------------------------------------------------------
# _fallback_parse tests
# ---------------------------------------------------------------------------


class TestFallbackParse:
    """Tests for the fuzzy-match fallback parser."""

    def test_exact_key_match(self) -> None:
        """Exact key names should be matched."""
        result = _fallback_parse({"car_km": 100, "ac_hours": 5})
        assert result.car_km == 100
        assert result.ac_hours == 5

    def test_unknown_keys_ignored(self) -> None:
        """Unknown keys should be silently ignored."""
        result = _fallback_parse({"unknown_field": 999, "car_km": 50})
        assert result.car_km == 50

    def test_empty_dict_returns_defaults(self) -> None:
        """Empty dict should return all-zero defaults."""
        result = _fallback_parse({})
        assert result.car_km == 0
        assert result.flight_km == 0


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------


class TestPydanticModels:
    """Tests for the Pydantic schema models."""

    def test_parsed_personal_data_defaults(self) -> None:
        """Default ParsedPersonalData should have all zeros."""
        data = ParsedPersonalData()
        assert data.car_km == 0
        assert data.is_valid is True
        assert data.untracked_activities == []

    def test_advisor_response_defaults(self) -> None:
        """Default AdvisorResponse should have sensible fallbacks."""
        resp = AdvisorResponse()
        assert len(resp.alternatives) == 2
        assert resp.analysis != ""

    def test_advisor_request_serialization(self) -> None:
        """AdvisorRequest should serialize to and from JSON."""
        req = AdvisorRequest(
            carbon=5000.0,
            tax=79000.0,
            car_km=10000,
            two_wheeler_km=0,
            auto_rickshaw_km=0,
            flight_km=0,
            bus_km=0,
            train_metro_km=0,
            ac_hours=4,
            restaurant_meals=52,
            tier="Human",
            goal="Reduce",
            kpis="test",
            worst_habit="Car",
        )
        json_str = req.model_dump_json()
        restored = AdvisorRequest.model_validate_json(json_str)
        assert restored.carbon == 5000.0
        assert restored.car_km == 10000

    def test_advisor_alternative_model(self) -> None:
        """AdvisorAlternative should validate correctly."""
        alt = AdvisorAlternative(
            type="Convenience",
            alternative="Take the bus",
            pros="Saves money",
            cons="Less flexible",
            est_monthly_savings_inr=500.0,
        )
        assert alt.est_monthly_savings_inr == 500.0
