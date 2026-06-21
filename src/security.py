"""
Security validation logic to ensure SAST Evaluator compliance and prevent prompt injection.
"""

import html
import re


def sanitize_input(text: str, max_length: int = 500) -> str:
    """
    Sanitize raw user input to prevent LLM prompt injection and XSS vulnerabilities.
    Strips HTML tags, escapes malicious characters, and truncates the string.

    Args:
        text: Raw input string from the user.
        max_length: Maximum allowed character length for the input. Defaults to 500.

    Returns:
        A sanitized, safe string ready for LLM ingestion.
    """
    if not isinstance(text, str):
        return ""

    # 1. Truncate strictly to max_length
    text = text[:max_length]

    # 2. Strip simple HTML tags via regex
    text = re.sub(r"<[^>]*>", "", text)

    # 3. Escape malicious/structural characters
    text = html.escape(text, quote=True)

    # 4. Remove curly braces to prevent prompt template injection
    text = text.replace("{", "").replace("}", "")

    return text.strip()
