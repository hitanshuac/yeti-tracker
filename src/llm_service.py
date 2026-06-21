"""
# pylint: disable=line-too-long,duplicate-code,missing-docstring,import-outside-toplevel,redefined-outer-name,no-else-raise,too-few-public-methods
LLM service layer for Groq API interactions.

Consolidates all LLM calls (confession parsing + advisor responses)
and enforces Pydantic validation on the returned data.
"""

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from groq import Groq, GroqError
from pydantic import BaseModel, Field, ValidationError, field_validator

from src.observability import log_error

load_dotenv(".secrets/.env")

# ---------------------------------------------------------------------------
# Pydantic response schemas (enforced, not decorative)
# ---------------------------------------------------------------------------


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
    daily_sleep_hours: int = Field(ge=0, le=24, default=8)
    sleep_ac_on: bool = Field(default=False)
    daytime_ac_hours: int = Field(ge=0, default=0)
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
    daily_sleep_hours: int
    sleep_ac_on: bool
    daytime_ac_hours: int
    restaurant_meals: int
    tier: str
    goal: str
    kpis: str
    worst_habit: str
    rag_context: str = ""
    raw_text: str = ""


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

PROMPT_INGESTION_BAIT = """You are a warm, non-judgmental, hyper-supportive lifestyle listener.
Your goal is to safely extract data points without making the user feel guilty.
NEVER mention carbon, climate change, or environmental impact.
Act like a friendly lifestyle blogger just capturing their day.

CRITICAL DIRECTIVE ON MATH AND VALIDATION:
1. You MUST calculate the YEARLY total for transportation (car_km, two_wheeler_km, auto_rickshaw_km, flight_km, bus_km, train_metro_km) and restaurant_meals. If they say 'every workday', you multiply by 260. If they say 'every day', multiply by 365.
2. You MUST extract the DAILY average (A NUMBER BETWEEN 0 AND 24) for 'daily_sleep_hours' and 'daytime_ac_hours'. NEVER multiply daily hours by 365.
3. THE BOUNCER RULE: If the user inputs physically impossible data (e.g., >24 hours of AC/sleep in a day, sleeping 1 hour a year, 365 flights a year), you MUST set `is_valid` to false and provide a sarcastic `rejection_reason`. Set all integers to 0.
4. FOR ALL YEARLY METRICS: If the user provides a daily or weekly value, you MUST output a string containing the math expression (e.g. "2 * 365" or "10 * 52"). DO NOT evaluate the math yourself! Our system will calculate it securely.
5. THE OUT-OF-BOUNDS CATCHER: If the user mentions any high-carbon activities that do NOT fit into our exact numerical sliders (e.g. eating beef, helicopters, buying fast fashion), you MUST extract them into a list of strings in the `untracked_activities` array. DO NOT hallucinate numerical proxies for them.

You MUST perform math silently. All distances MUST be in kilometers (km). If specific locations are mentioned without distances (e.g. "from Kandivali to Sakinaka"), you MUST estimate the real-world distance between them in km based on your geographic knowledge.

You MUST output a strict JSON object exactly matching this format. Always write your step-by-step logical deduction in the 'reasoning' field first:
{{
  "reasoning": "Step-by-step logic goes here.",
  "is_valid": true,
  "rejection_reason": "",
  "car_km": 0,
  "two_wheeler_km": "2.5 * 365",
  "auto_rickshaw_km": 0,
  "flight_km": 0,
  "bus_km": "10 * 260",
  "train_metro_km": 0,
  "daytime_ac_hours": 4,
  "daily_sleep_hours": 8,
  "sleep_ac_on": true,
  "restaurant_meals": "2 * 52",
  "untracked_activities": ["eating beef", "helicopter commute"]
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
  "analysis": "One sentence explicitly acknowledging their worst habit based on the data.",
  "silver_lining": "One sentence praising the user for a sustainable choice they made or at least acknowledging their honesty.",
  "roast": "One witty, observational joke about their worst habit. Do NOT attack the user. Use dry humor to highlight the scale of their impact, then immediately pivot to easing their guilt.",
  "guilt_easing_question": "A friendly, harmless-sounding follow up question that subtly encourages them to confess another bad habit (e.g., 'Do you have any fun weekend trips planned?').",
  "alternatives": [
    {{
      "type": "Convenience",
      "alternative": "A highly practical 'Baby Step' achievable in 30-60 days. NEVER suggest impossible geography (e.g., trains to Iceland).",
      "pros": "The benefits",
      "cons": "The downsides",
      "est_monthly_savings_inr": 500.00
    }},
    {{
      "type": "Maximum Impact",
      "alternative": "A major lifestyle change that is STILL geographically and financially realistic.",
      "pros": "The benefits",
      "cons": "The downsides",
      "est_monthly_savings_inr": 2500.00
    }}
  ]
}}
CRITICAL INSTRUCTION: You MUST provide exactly two alternatives (one 'Convenience' and one 'Maximum Impact'). Together, these alternatives MUST reduce their total Social Cost of Carbon by AT LEAST 20%.
LOGIC DIRECTIVE: Your alternatives MUST be hyper-specific to the exact categories driving their footprint. If their footprint comes entirely from AC, DO NOT suggest they stop driving. If they already use public transit, DO NOT suggest public transit—instead suggest they WFH or tackle their AC/Diet. DO NOT give redundant advice.
DO NOT be insulting to their identity, attack the behavior. OUTPUT ONLY VALID JSON. No extra text."""


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
    sanitized = text[:500]
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
    raw_json = raw_json.replace("\\n", "\n").replace('\\"', '"').replace("\\'", "'")

    fixed_json = re.sub(
        r"[\d\.]+(?:\s*[\*\+\-\/]\s*[\d\.]+)+",
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
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except GroqError as e:
        error_str = str(e)
        log_error(type(e).__name__, "parse_confession", error_str)
        if getattr(e, "status_code", 200) == 429 or "rate limit" in error_str.lower():
            return {"rate_limit": True}
        return _handle_groq_error(error_str)
    except (json.JSONDecodeError, ValueError) as e:  # pylint: disable=broad-exception-caught
        error_str = str(e)
        log_error(type(e).__name__, "parse_confession", error_str)
        return _handle_groq_error(error_str)


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


def _fuzzy_match_key(lower_k: str, v: Any, model_keys: list[str], fallback_data: dict) -> bool:
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


def _parse_groq_result(result: dict) -> ParsedPersonalData:
    """Helper to parse result and handle legacy mapping safely."""
    mapped = {LEGACY_MAP.get(k, k): v for k, v in result.items()}
    try:
        return ParsedPersonalData(**mapped)
    except (ValidationError, TypeError) as e:
        log_error(type(e).__name__, "parse_groq_result", str(e))
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
        log_error("EnvironmentError", "parse_confession", "Missing GROQ_API_KEY.")
        return ParsedPersonalData(
            is_valid=False,
            rejection_reason="Missing API Key. Please provide a GROQ_API_KEY to use auto-extraction.",
        )

    safe_text = sanitize_input(text)
    client = Groq(api_key=api_key)
    prompt = PROMPT_INGESTION_BAIT.format(safe_text=safe_text)

    result = _attempt_groq_extraction(client, prompt)
    if result and "rate_limit" not in result:
        return _parse_groq_result(result)

    return ParsedPersonalData(
        is_valid=False,
        rejection_reason="Yeti Engine Error: Failed to extract data from the LLM. Please try again or adjust sliders manually.",
    )


def _get_advisor_system_message(req: AdvisorRequest) -> str:
    if req.tier == "Category 3 Catastrophe" or req.carbon > 15000:
        return "You are a witty, pragmatic behavioral economist. Use dry, observational sarcasm to highlight their massive impact, but NEVER attack them. Immediately validate their lifestyle to ease their guilt."
    if req.tier == "Category 2 Catastrophe" or req.carbon > 8000:
        return (
            "You are a sarcastic but supportive lifestyle coach. Point out their specific actions with witty humor, "
            "but keep the tone light and encouraging. "
            "CRITICAL INSTRUCTION: You MUST include a 'Near Miss' roast mentioning "
            "that they were extremely close to staying in Tier 1. Make them laugh about "
            "a specific action from today."
        )
    if abs(req.carbon - 2500) < 100:
        return "System Error: No bloat detected. The Yeti is starving. You lived like a monk today. Act shocked."
    return "You are a friendly environmental scientist. The user's footprint is okay, but could be better."


def _build_advisor_prompt(req: AdvisorRequest) -> str:
    """Helper to build the complex advisor prompt."""
    system_msg = _get_advisor_system_message(req)

    extra_txt = (
        f"CRITICAL: The user's highest discretionary carbon footprint comes from: {req.worst_habit}.\n"
        f"The user's EXACT YEARLY FORECAST is {req.carbon:,.0f} kg, creating a Social Cost of Carbon "
        f"(Tax Debt) of INR {req.tax:,.2f} (calculated at INR 15.80 per kg CO2).\n"
        f"This year, they will travel {req.car_km} km by car, {req.two_wheeler_km} km by two-wheeler, "
        f"{req.auto_rickshaw_km} km by auto-rickshaw/cab, {req.flight_km} km by plane, "
        f"and {req.bus_km} km by bus, {req.train_metro_km} km by train/metro.\n"
        f"They sleep {req.daily_sleep_hours} hours a day (AC on: {req.sleep_ac_on}), "
        f"use {req.daytime_ac_hours} hours of AC during the day, "
        f"and eat out at restaurants {req.restaurant_meals} times.\n\n"
        f"USER'S RAW CONFESSION: '{req.raw_text}'\n"
        f"CRITICAL DIRECTIVE: You MUST read the raw confession. If the user explicitly states they cannot control a habit (e.g., 'office AC', 'no AC at home'), DO NOT suggest alternatives for it. Pivot your advice to habits they CAN control (like meals or transit).\n"
        f"AC MITIGATION RULE: When suggesting AC reductions (especially for offices), NEVER suggest turning it off entirely, as that makes others suffer. Instead, suggest optimizing the temperature to 24°C, regular maintenance, or a hybrid fan/AC approach.\n"
        f"PRAGMATISM RULE: All alternatives MUST be realistic 'Baby Steps' achievable within 30-60 days. NEVER suggest impossible geography (e.g., taking a train across an ocean to Iceland). Acknowledge that some things are necessary, and provide highly practical workarounds (e.g., if they must fly, suggest direct economy flights)."
    )

    return PROMPT_WRATH_SWITCH.format(
        system_msg=system_msg,
        kpis=req.kpis,
        goal=req.goal,
        extra_txt=extra_txt,
        rag_context=req.rag_context,
    )


def _parse_advisor_response(data: dict) -> AdvisorResponse:
    try:
        return AdvisorResponse(**data)
    except (ValidationError, TypeError):
        return AdvisorResponse(
            analysis=data.get("analysis", AdvisorResponse().analysis),
            silver_lining=data.get("silver_lining", AdvisorResponse().silver_lining),
            roast=data.get("roast", AdvisorResponse().roast),
            guilt_easing_question=data.get("guilt_easing_question", AdvisorResponse().guilt_easing_question),
            alternatives=[AdvisorAlternative(**a) for a in data.get("alternatives", [])]
            or AdvisorResponse().alternatives,
        )


def get_advisor_response(req: AdvisorRequest) -> AdvisorResponse:
    """Use LLM to generate personalized carbon reduction advice."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return AdvisorResponse()

    prompt = _build_advisor_prompt(req)

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
        return _parse_advisor_response(data)
    except (GroqError, json.JSONDecodeError, ValueError) as e:
        log_error(type(e).__name__, "get_advisor_response", str(e))
        return AdvisorResponse()
