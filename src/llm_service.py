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

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pydantic response schemas (enforced, not decorative)
# ---------------------------------------------------------------------------


class ParsedPersonalData(BaseModel):
    """Schema for parsed lifestyle activities from natural language."""

    miles_driven: int = Field(ge=0, default=0)
    flight_miles: int = Field(ge=0, default=0)
    transit_miles: int = Field(ge=0, default=0)
    ac_hours: int = Field(ge=0, default=0)
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

    silver_lining: str = "I appreciate your honesty."
    roast: str = "But your carbon footprint is a total disaster."
    guilt_easing_question: str = "Are there any other guilty pleasures you want to share?"
    alternatives: list[AdvisorAlternative] = Field(
        default_factory=lambda: [
            AdvisorAlternative(
                type="Convenience",
                alternative="Work from home 2 days a week",
                pros="Save time and gas",
                cons="Less social interaction",
                est_monthly_savings_inr=500.0,
            ),
            AdvisorAlternative(
                type="Maximum Impact",
                alternative="Sell your car and bike everywhere",
                pros="Massive carbon savings",
                cons="Extremely inconvenient in winter",
                est_monthly_savings_inr=2500.0,
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
Estimate distances in km. If specific locations are mentioned without distances (e.g. "from Kandivali to Sakinaka"),
you MUST estimate the real-world distance between them in km based on your geographic knowledge.
You MUST output a strict JSON object exactly matching this format:
{{
  "miles_driven": 0,
  "flight_miles": 0,
  "transit_miles": 0,
  "ac_hours": 0,
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
  "roast": "One witty, aggressive observation calling out their massive forecast and their history.",
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
            return str(int(eval(expr)))
        except Exception:
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
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        error_str = str(e)
        _log_llm_error(type(e).__name__, "parse_confession", error_str)

        if "failed_generation" in error_str:
            recovered = _recover_failed_generation(error_str)
            if recovered:
                return recovered
        return None


def parse_confession(text: str) -> ParsedPersonalData:
    """Use LLM to extract structured data from messy natural language.

    Args:
        text: Raw user confession text.

    Returns:
        A validated ParsedPersonalData model.
    """
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        _log_llm_error("EnvironmentError", "parse_confession", "Missing GROQ_API_KEY.")
        return ParsedPersonalData()

    safe_text = sanitize_input(text)
    client = Groq(api_key=api_key)
    prompt = PROMPT_INGESTION_BAIT.format(safe_text=safe_text)

    for _attempt in range(3):
        result = _attempt_groq_extraction(client, prompt)
        if result:
            try:
                return ParsedPersonalData(**result)
            except Exception:
                return ParsedPersonalData(
                    **{
                        k: max(0, int(float(v))) if isinstance(v, int | float) else 0
                        for k, v in result.items()
                        if k in ParsedPersonalData.model_fields
                    }
                )
        time.sleep(1)

    return ParsedPersonalData()


def get_advisor_response(
    carbon: float,
    tax: float,
    car_miles: int,
    flight_miles: int,
    transit_miles: int,
    ac: int,
    restaurant_meals: int,
    tier: str,
    goal: str,
    kpis: str,
    rag_context: str = "",
) -> AdvisorResponse:
    """Use LLM to generate personalized carbon reduction advice.

    Args:
        carbon: Yearly CO2 in kg.
        tax: Yearly carbon tax in INR.
        car_miles: Yearly car km.
        flight_miles: Yearly flight km.
        transit_miles: Yearly transit km.
        ac: Yearly AC hours.
        restaurant_meals: Yearly restaurant meals.
        tier: Current gamification tier string.
        goal: User's stated goal.
        kpis: Historical accountability KPIs string.
        rag_context: RAG context from dataset.

    Returns:
        A validated AdvisorResponse model.
    """
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return AdvisorResponse()

    if carbon > 15000:
        system_msg = "You are a ruthless climate auditor. The user is actively destroying the planet."
    elif carbon > 8000:
        system_msg = "You are a strict, disappointed advisor. The user is careless."
    else:
        system_msg = "You are a friendly environmental scientist. The user's footprint is okay, but could be better."

    extra_txt = (
        f"The user's EXACT YEARLY FORECAST is {carbon:,.0f} kg, creating a Social Cost of Carbon "
        f"(Tax Debt) of ₹{tax:,.2f} INR (calculated at 15.80 INR per kg CO2).\n"
        f"This year, they will travel {car_miles} km by car, {flight_miles} km by plane, "
        f"and {transit_miles} km by train/bus.\n"
        f"They will use the AC for {ac} hours, and eat out at restaurants {restaurant_meals} times."
    )

    prompt = PROMPT_WRATH_SWITCH.format(
        system_msg=system_msg,
        kpis=kpis,
        goal=goal,
        extra_txt=extra_txt,
        rag_context=rag_context,
    )

    client = Groq(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
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
