"""
LLM service layer for Groq API interactions.

Consolidates all LLM calls (confession parsing + advisor responses)
and enforces Pydantic validation on the returned data.
"""

import json
import os
import re
import time
from typing import Any

from dotenv import load_dotenv
from groq import Groq, GroqError
from pydantic import BaseModel, Field

load_dotenv(".secrets/.env")

# ---------------------------------------------------------------------------
# Pydantic response schemas (enforced, not decorative)
# ---------------------------------------------------------------------------


class ParsedPersonalData(BaseModel):
    """Schema for parsed lifestyle activities from natural language."""

    car_km: int = Field(ge=0, default=0)
    flight_km: int = Field(ge=0, default=0)
    transit_km: int = Field(ge=0, default=0)
    daily_sleep_hours: int = Field(ge=0, le=24, default=8)
    sleep_ac_on: bool = Field(default=False)
    daytime_ac_hours: int = Field(ge=0, default=0)
    restaurant_meals: int = Field(ge=0, default=0)


class AdvisorAlternative(BaseModel):
    """A single reduction strategy alternative."""

    type: str
    alternative: str
    pros: str
    cons: str
    est_monthly_savings_inr: float


class AdvisorResponse(BaseModel):
    """Schema for the Yeti Advisor's full response."""

    silver_lining: str = "You're being honest about your habits — that's the first step."
    roast: str = "But let's see if we can do better, shall we?"
    guilt_easing_question: str = "Tell me more about your daily routine — any hidden habits?"
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


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

PROMPT_INGESTION_BAIT = """You are a warm, non-judgmental, hyper-supportive lifestyle listener.
Your goal is to safely extract data points without making the user feel guilty.
NEVER mention carbon, climate change, or environmental impact.
Act like a friendly lifestyle blogger just capturing their day.
CRITICAL: You MUST calculate the YEARLY total for each category based on the text.
If they say 'once a month', multiply by 12. If they say 'every workday', multiply by 260.
If frequency is unspecified, assume the stated number is their yearly total.
You MUST perform the math silently and output ONLY the final computed integer.
DO NOT output formulas (e.g., no '260 * 10'). The JSON values MUST be raw integers.
All distances MUST be in kilometers (km). If specific locations are mentioned without distances
(e.g. "from Kandivali to Sakinaka"), you MUST estimate the real-world distance between them
in km based on your geographic knowledge.
For 'daily_sleep_hours', extract the average number of hours they sleep per night.
For 'sleep_ac_on', extract whether they mention sleeping with the AC or cooler on (true/false).
For 'daytime_ac_hours', extract the average number of hours they use the AC or cooler during the day while awake.
You MUST output a strict JSON object exactly matching this format:
{{
  "car_km": 0,
  "flight_km": 0,
  "transit_km": 0,
  "daily_sleep_hours": 8,
  "sleep_ac_on": false,
  "daytime_ac_hours": 0,
  "restaurant_meals": 0
}}
Text: {safe_text}"""

PROMPT_WRATH_SWITCH = """{system_msg}
The user just tried to hide behind a friendly conversation. They confessed to their actions.
[SILENT ACCOUNTABILITY METRICS]: {kpis}
The user's primary goal today is: {goal}. YOU MUST TAILOR YOUR ADVICE SPECIFICALLY TO THIS GOAL.
{extra_txt}
{rag_context}
You must output a strict JSON object matching this schema:
{{
  "silver_lining": "One sentence praising the user for a sustainable choice they made or at least acknowledging their honesty.",
  "roast": "One witty, aggressive observation calling out their massive forecast. DO NOT use abstract kg measurements. INVENT a unique, highly specific Indian analogy based EXACTLY on their worst habit (e.g. if they flew, talk about aviation fuel over Mumbai; if they used AC, talk about collapsing the local grid). NEVER repeat the same analogy twice.",
  "guilt_easing_question": "A friendly, harmless-sounding follow up question that subtly encourages them to confess another bad habit (e.g., 'Do you have any fun weekend trips planned?').",
  "alternatives": [
    {{
      "type": "Convenience",
      "alternative": "A simple baby step that is extremely easy to adopt",
      "pros": "The benefits",
      "cons": "The downsides",
      "est_monthly_savings_inr": 500.00
    }},
    {{
      "type": "Maximum Impact",
      "alternative": "A major lifestyle change that guarantees massive carbon savings",
      "pros": "The benefits",
      "cons": "The downsides",
      "est_monthly_savings_inr": 2500.00
    }}
  ]
}}
CRITICAL INSTRUCTION: You MUST provide exactly two alternatives (one 'Convenience' and one 'Maximum Impact'). Together, these alternatives MUST reduce their total Social Cost of Carbon by AT LEAST 20%.
LOGIC DIRECTIVE: Your alternatives MUST be hyper-specific to the exact categories driving their footprint. If their footprint comes entirely from AC, DO NOT suggest they stop driving. If they already use public transit, DO NOT suggest public transit—instead suggest they WFH or tackle their AC/Diet. DO NOT give redundant advice.
DO NOT be insulting to their identity, attack the behavior. OUTPUT ONLY VALID JSON. No extra text."""  # noqa: E501


# ---------------------------------------------------------------------------
# Input sanitization
# ---------------------------------------------------------------------------


def sanitize_input(text: str) -> str:
    """Sanitize raw input text to mitigate CWE-74 prompt injection.

    Args:
        text: Raw user input.

    Returns:
        Sanitized string, truncated to 1000 chars.
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    sanitized = text[:1000]
    for char in ["<", ">", "{", "}"]:
        sanitized = sanitized.replace(char, "")
    return sanitized.strip()


# ---------------------------------------------------------------------------
# Math expression recovery from failed LLM generation
# ---------------------------------------------------------------------------


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


def _recover_failed_generation(error_msg: str) -> dict | None:
    """Extract and fix the failed_generation JSON from a Groq 400 error."""
    match = re.search(r"'failed_generation':\s*'(.*?)'}}", error_msg, re.DOTALL)
    if not match:
        return None

    raw_json = match.group(1)
    raw_json = raw_json.replace("\\n", "\n").replace('\\"', '"')

    fixed_json = re.sub(
        r"[\d]+(?:\s*[\*\+\-\/]\s*[\d\.]+)+",
        _safe_eval_math_expr,
        raw_json,
    )

    try:
        data = json.loads(fixed_json)
        return {k: int(float(v)) if isinstance(v, int | float) else v for k, v in data.items()}
    except (json.JSONDecodeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Groq API calls
# ---------------------------------------------------------------------------


def _handle_groq_error(error_str: str) -> dict | None:
    """Handle and try to recover from Groq extraction errors."""
    if "failed_generation" in error_str:
        recovered = _recover_failed_generation(error_str)
        if recovered:
            return recovered
    return None


def _attempt_groq_extraction(client: Any, prompt: str) -> dict | None:
    """Attempt a single Groq API call and handle recovery.

    Args:
        client: Initialized Groq client.
        prompt: The fully formatted prompt string.

    Returns:
        Parsed JSON dict or None on failure.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except GroqError as e:
        error_str = str(e)
        _log_llm_error(type(e).__name__, "parse_confession", error_str)
        if getattr(e, "status_code", 200) == 429 or "rate limit" in error_str.lower():
            return {"rate_limit": True}
        return _handle_groq_error(error_str)
    except Exception as e:  # pylint: disable=broad-exception-caught
        error_str = str(e)
        _log_llm_error(type(e).__name__, "parse_confession", error_str)
        return _handle_groq_error(error_str)


LEGACY_MAP = {
    "miles_driven": "car_km",
    "flight_miles": "flight_km",
    "transit_miles": "transit_km",
}


def _fallback_parse(mapped: dict) -> ParsedPersonalData:
    """Fallback parsing logic for messy LLM outputs."""
    fallback_data = {}
    model_keys = list(ParsedPersonalData.model_fields.keys())
    for k, v in mapped.items():
        lower_k = str(k).lower().strip()
        # Fuzzy match to handle capitalization/spacing
        for mk in model_keys:
            if lower_k == mk.lower() or lower_k.replace(" ", "_") == mk.lower():
                try:
                    if isinstance(v, list) and len(v) > 0:
                        v = v[0]
                    # Safely coerce strings/floats to int
                    fallback_data[mk] = max(0, int(float(v)))
                except (ValueError, TypeError):
                    pass  # Leave as default 0
                break
    return ParsedPersonalData(**fallback_data)


def _parse_groq_result(result: dict) -> ParsedPersonalData:
    """Helper to parse result and handle legacy mapping safely."""
    mapped = {LEGACY_MAP.get(k, k): v for k, v in result.items()}
    try:
        return ParsedPersonalData(**mapped)
    except Exception as e:  # pylint: disable=broad-exception-caught
        _log_llm_error(type(e).__name__, "parse_groq_result", str(e))
        return _fallback_parse(mapped)


def parse_confession(text: str) -> ParsedPersonalData:
    """Use LLM to extract structured data from messy natural language.

    Args:
        text: Raw user confession text.

    Returns:
        A validated ParsedPersonalData model.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        _log_llm_error("EnvironmentError", "parse_confession", "Missing GROQ_API_KEY.")
        return ParsedPersonalData()

    safe_text = sanitize_input(text)
    client = Groq(api_key=api_key)
    prompt = PROMPT_INGESTION_BAIT.format(safe_text=safe_text)

    for _attempt in range(3):
        result = _attempt_groq_extraction(client, prompt)
        if result and "rate_limit" in result:
            break  # Fast-fail on rate limits instead of burning retries
        if result:
            return _parse_groq_result(result)
        time.sleep(1)

    return ParsedPersonalData()


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def _build_advisor_prompt(
    carbon: float,
    tax: float,
    car_km: int,
    flight_km: int,
    transit_km: int,
    daily_sleep_hours: int,
    sleep_ac_on: bool,
    daytime_ac_hours: int,
    restaurant_meals: int,
    tier: str,
    goal: str,
    kpis: str,
    rag_context: str,
) -> str:
    """Helper to build the complex advisor prompt."""
    if tier == "Category 3 Catastrophe" or carbon > 15000:
        system_msg = "You are a ruthless climate auditor. The user is actively destroying the planet."
    elif tier == "Category 2 Catastrophe" or carbon > 8000:
        system_msg = (
            "You are a strict, disappointed advisor. The user is careless. "
            "CRITICAL INSTRUCTION: You MUST include a 'Near Miss' roast mentioning "
            "that they were extremely close to staying in Tier 1. Make them regret a "
            "specific action from today (e.g. 'If you had turned off the Daytime AC "
            "45 minutes earlier, you would have survived.')."
        )
    elif abs(carbon - 2500) < 100:
        system_msg = "System Error: No bloat detected. The Yeti is starving. You lived like a monk today. Act shocked."
    else:
        system_msg = "You are a friendly environmental scientist. The user's footprint is okay, but could be better."

    extra_txt = (
        f"The user's EXACT YEARLY FORECAST is {carbon:,.0f} kg, creating a Social Cost of Carbon "
        f"(Tax Debt) of INR {tax:,.2f} (calculated at INR 15.80 per kg CO2).\n"
        f"This year, they will travel {car_km} km by car, {flight_km} km by plane, "
        f"and {transit_km} km by train/bus.\n"
        f"They sleep {daily_sleep_hours} hours a day (AC on: {sleep_ac_on}), "
        f"use {daytime_ac_hours} hours of AC during the day, "
        f"and eat out at restaurants {restaurant_meals} times."
    )

    return PROMPT_WRATH_SWITCH.format(
        system_msg=system_msg,
        kpis=kpis,
        goal=goal,
        extra_txt=extra_txt,
        rag_context=rag_context,
    )


# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
def get_advisor_response(
    carbon: float,
    tax: float,
    car_km: int,
    flight_km: int,
    transit_km: int,
    daily_sleep_hours: int,
    sleep_ac_on: bool,
    daytime_ac_hours: int,
    restaurant_meals: int,
    tier: str,
    goal: str,
    kpis: str,
    rag_context: str = "",
) -> AdvisorResponse:
    """Use LLM to generate personalized carbon reduction advice."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return AdvisorResponse()

    prompt = _build_advisor_prompt(
        carbon,
        tax,
        car_km,
        flight_km,
        transit_km,
        daily_sleep_hours,
        sleep_ac_on,
        daytime_ac_hours,
        restaurant_meals,
        tier,
        goal,
        kpis,
        rag_context,
    )

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        try:
            return AdvisorResponse(**data)
        except Exception:
            # Graceful partial parse — use defaults for missing fields
            return AdvisorResponse(
                silver_lining=data.get("silver_lining", AdvisorResponse().silver_lining),
                roast=data.get("roast", AdvisorResponse().roast),
                guilt_easing_question=data.get("guilt_easing_question", AdvisorResponse().guilt_easing_question),
                alternatives=[AdvisorAlternative(**a) for a in data.get("alternatives", [])]
                or AdvisorResponse().alternatives,
            )
    except Exception as e:
        _log_llm_error(type(e).__name__, "get_advisor_response", str(e))
        return AdvisorResponse()


# ---------------------------------------------------------------------------
# Internal error logging
# ---------------------------------------------------------------------------


def _log_llm_error(error_type: str, component: str, message: str) -> None:
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
            "error_type": error_type,
            "component": component,
            "message": message,
            "status": "UNRESOLVED",
            "resolution_strategy": None,
        }
    )

    temp_file = f"{log_file}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    os.replace(temp_file, log_file)
