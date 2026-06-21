"""
External API boundaries for Groq LLM integration.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq, GroqError

from src.llm.models import AdvisorRequest, AdvisorResponse, ParsedPersonalData
from src.llm.parsers import parse_groq_result, recover_failed_generation, sanitize_input
from src.llm.prompts import PROMPT_INGESTION_BAIT, PROMPT_WRATH_SWITCH
from src.observability import log_error

load_dotenv(".secrets/.env")


MODELS = ["llama-3.3-70b-versatile", "llama3-8b-8192", "mixtral-8x7b-32768"]


def _get_api_keys() -> list[str]:
    """Retrieve all available Groq API keys from the environment."""
    keys = [os.environ.get("GROQ_API_KEY")]
    keys.extend([os.environ.get(f"GROQ_API_KEY_{i}") for i in (2, 3, 4, 5)])
    return [k for k in keys if k]


def _handle_groq_error(error_str: str) -> dict | None:
    """Handle and try to recover from Groq extraction errors."""
    if "failed_generation" in error_str:
        recovered = recover_failed_generation(error_str)
        if recovered:
            return recovered
    return None


def _is_rate_limit(e: GroqError) -> bool:
    """Check if the GroqError is a rate limit."""
    return getattr(e, "status_code", 200) == 429 or "rate limit" in str(e).lower()


def _attempt_single_call(
    client: Groq, model: str, messages: list[dict], caller: str
) -> dict | None | str:
    """Attempt a single LLM call. Returns dict (success), 'RATE_LIMIT' (exhausted), or None (failed)."""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0 if caller == "parse_confession" else 0.7,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except GroqError as e:
        error_str = str(e)
        log_error(type(e).__name__, caller, f"Model {model} failed: {error_str}")
        if _is_rate_limit(e):
            return "RATE_LIMIT"
        return _handle_groq_error(error_str)
    except (json.JSONDecodeError, ValueError) as e:
        error_str = str(e)
        log_error(type(e).__name__, caller, error_str)
        return _handle_groq_error(error_str)


def _execute_with_cascading_fallback(messages: list[dict], caller: str) -> dict | None:
    """Execute Groq call with cascading fallbacks across models and API keys."""
    keys = _get_api_keys()
    if not keys:
        log_error("EnvironmentError", caller, "Missing GROQ_API_KEY")
        return None

    for model in MODELS:
        for api_key in keys:
            client = Groq(api_key=api_key)
            result = _attempt_single_call(client, model, messages, caller)
            if isinstance(result, dict):
                return result
            # If RATE_LIMIT or None, cascade dynamically

    # If all keys and all models fail (total exhaustion)
    return {"rate_limit": True}


def parse_confession(text: str) -> ParsedPersonalData:
    """Use LLM to extract structured data from messy natural language."""
    safe_text = sanitize_input(text)
    prompt = PROMPT_INGESTION_BAIT.format(safe_text=safe_text)
    messages = [{"role": "user", "content": prompt}]

    result = _execute_with_cascading_fallback(messages, "parse_confession")

    if result is None:
        return ParsedPersonalData(
            is_valid=False,
            rejection_reason="Missing API Key. Please provide a GROQ_API_KEY to use auto-extraction.",
        )

    if "rate_limit" in result:
        return ParsedPersonalData(
            is_valid=False,
            rejection_reason="Rate Limit Exceeded: The Yeti is currently exhausted across all models and keys. Please try again later.",
        )

    return parse_groq_result(result)


def _is_severe_catastrophe(req: AdvisorRequest) -> bool:
    return req.tier == "Category 3 Catastrophe" or req.carbon > 15000


def _is_moderate_catastrophe(req: AdvisorRequest) -> bool:
    return req.tier == "Category 2 Catastrophe" or req.carbon > 8000


def _get_advisor_system_message(req: AdvisorRequest) -> str:
    if _is_severe_catastrophe(req):
        return (
            "You are a witty, pragmatic behavioral economist. Use dry, observational sarcasm "
            "to highlight their massive impact, but NEVER attack them. "
            "Immediately validate their lifestyle to ease their guilt."
        )
    if _is_moderate_catastrophe(req):
        return (
            "You are a sharp, realistic sustainability coach. Acknowledge their effort, "
            "but clearly state where they are over-consuming using gentle humor."
        )
    return (
        "You are an encouraging, supportive guide. "
        "They are doing great. Keep the humor light and focus on taking the next small step."
    )


def _build_advisor_prompt(req: AdvisorRequest, system_msg: str) -> str:
    extra_txt = f"The user replied: {req.raw_text}" if req.raw_text else ""
    rag_context = (
        f"RAG CONTEXT (Integrate these strictly):\n{req.rag_context}"
        if req.rag_context
        else ""
    )

    return PROMPT_WRATH_SWITCH.format(
        system_msg=system_msg,
        kpis=req.kpis,
        goal=req.goal,
        extra_txt=extra_txt,
        rag_context=rag_context,
    )


def get_advisor_response(req: AdvisorRequest) -> AdvisorResponse:
    """Generate dynamic reduction advice based on user's specific data."""
    system_msg = _get_advisor_system_message(req)
    prompt = _build_advisor_prompt(req, system_msg)

    messages = [
        {"role": "user", "content": prompt},
        {"role": "user", "content": f"Their worst habit is: {req.worst_habit}"},
    ]

    result = _execute_with_cascading_fallback(messages, "get_advisor_response")

    if result is None:
        return AdvisorResponse()

    if "rate_limit" in result:
        return AdvisorResponse(
            analysis="System Overload: The Yeti is currently exhausted from processing too many confessions.",
            silver_lining="The good news is, you can still view your deterministic calculations above.",
            roast="Our servers are melting faster than the ice caps.",
            guilt_easing_question="Take a breath, adjust your sliders, and try generating advice again in a few minutes.",
        )

    try:
        return AdvisorResponse.model_validate(result)
    except (ValueError, TypeError) as e:
        log_error(type(e).__name__, "get_advisor_response", str(e))
        return AdvisorResponse()
