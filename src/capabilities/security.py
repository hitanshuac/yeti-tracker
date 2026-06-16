"""
Security module for sanitizing inputs and preventing CWE-74 Prompt Injection.
"""

import re
import unicodedata

from fastapi import HTTPException

# Maximum allowed length for input text to prevent DoS via massive payloads
MAX_INPUT_LENGTH = 2000

# Common prompt injection signatures
PROMPT_INJECTION_SIGNATURES = [
    r"(?i)ignore\s+all\s+previous\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)you\s+are\s+now",
    r"(?i)bypass\s+restrictions",
    r"(?i)forget\s+everything",
]


def sanitize_input(text: str) -> str:
    """
    Sanitizes raw input text to mitigate CWE-74 prompt injection and other attacks.

    Args:
        text: Raw input string from the user.

    Returns:
        Sanitized string safe for LLM consumption.

    Raises:
        HTTPException: If malicious patterns are detected or input is invalid.
    """
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")

    # 1. Truncate to maximum length
    sanitized = text[:MAX_INPUT_LENGTH]

    # 2. Normalize unicode (removes obfuscated characters)
    sanitized = unicodedata.normalize("NFKC", sanitized)

    # 3. Strip control characters
    sanitized = "".join(ch for ch in sanitized if unicodedata.category(ch)[0] != "C")

    # 4. Check for known injection signatures
    for pattern in PROMPT_INJECTION_SIGNATURES:
        if re.search(pattern, sanitized):
            raise HTTPException(status_code=400, detail="Malicious input pattern detected.")

    return sanitized.strip()
