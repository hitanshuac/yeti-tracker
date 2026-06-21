"""
Parsing and sanitization logic for LLM service.
"""

import json
import re
from typing import Any

from pydantic import ValidationError

from src.llm.models import ParsedPersonalData
from src.observability import log_error


def sanitize_input(text: str) -> str:
    """Sanitize raw input text to mitigate CWE-74 prompt injection.

    Args:
        text: Raw user input.

    Returns:
        Sanitized string, truncated to 500 chars.
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    sanitized = text[:500]
    for char in ["<", ">", "{", "}"]:
        sanitized = sanitized.replace(char, "")
    return sanitized.strip()


def _safe_eval_math_expr(match: "re.Match") -> str:
    """Safely evaluate a simple arithmetic expression (e.g., '260 * 10')."""
    expr = match.group(0)
    if re.fullmatch(r"[\d\s\*\+\-\/\.]+", expr):
        try:
            # pylint: disable=eval-used
            return str(int(eval(expr)))
        except (SyntaxError, NameError, TypeError, ZeroDivisionError):
            return "0"
    return "0"


def recover_failed_generation(error_msg: str) -> dict | None:
    """Extract and fix the failed_generation JSON from a Groq 400 error."""
    match = re.search(r"'failed_generation':\s*'(.*?)'}}", error_msg, re.DOTALL)
    if not match:
        return None

    raw_json = match.group(1)
    raw_json = raw_json.replace("\\n", "\n").replace('\\"', '"').replace("\\'", "'")

    fixed_json = re.sub(
        r"[\d\.]+(?:\s*[\*\+\-\/]\s*[\d\.]+)+",
        _safe_eval_math_expr,
        raw_json,
    )

    try:
        data = json.loads(fixed_json)
        return {
            k: int(float(v)) if isinstance(v, int | float) else v
            for k, v in data.items()
        }
    except (json.JSONDecodeError, ValueError):
        return None


LEGACY_MAP = {
    "miles_driven": "car_km",
    "flight_miles": "flight_km",
    "transit_miles": "train_metro_km",
    "transit_km": "train_metro_km",
}


def _apply_fuzzy_value(mk: str, v: Any, fallback_data: dict) -> None:
    """Safely coerce and apply a fuzzy matched value."""
    try:
        if isinstance(v, list) and len(v) > 0:
            v = v[0]
        fallback_data[mk] = max(0, int(float(v)))
    except (ValueError, TypeError):
        pass


def _fuzzy_match_key(
    lower_k: str, v: Any, model_keys: list[str], fallback_data: dict
) -> bool:
    """Helper to perform fuzzy key matching for fallback parsing."""
    for mk in model_keys:
        if lower_k == mk.lower() or lower_k.replace(" ", "_") == mk.lower():
            _apply_fuzzy_value(mk, v, fallback_data)
            return True
    return False


def _fallback_parse(mapped: dict) -> ParsedPersonalData:
    """Fallback parsing logic for messy LLM outputs."""
    fallback_data = {}
    model_keys = list(ParsedPersonalData.model_fields.keys())
    for k, v in mapped.items():
        lower_k = str(k).lower().strip()
        _fuzzy_match_key(lower_k, v, model_keys, fallback_data)
    return ParsedPersonalData(**fallback_data)


def parse_groq_result(result: dict) -> ParsedPersonalData:
    """Helper to parse result and handle legacy mapping safely."""
    mapped = {LEGACY_MAP.get(k, k): v for k, v in result.items()}
    try:
        return ParsedPersonalData(**mapped)
    except (ValidationError, TypeError) as e:
        log_error(type(e).__name__, "parse_groq_result", str(e))
        return _fallback_parse(mapped)
