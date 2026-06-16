"""
Module for compacting and sanitizing LLM conversation context windows.
"""

import copy
import re
from typing import Any

SYSTEM_PROMPT = {"role": "system", "content": "You are a helpful AI."}

# Pre-compiled regex for boilerplate stripping to reduce cyclomatic complexity
BOILERPLATE_PATTERN = re.compile(
    r"^(Sure! |Sure, |Of course! |Of course, |Great question! |That's a great question! "
    r"|Absolutely! |Certainly! |I'd be happy to help! |I'd be happy to help you with that! "
    r"|Let me help you with that\. )"
)


def _strip_single_message(content: str) -> str:
    """
    Helper function to strip boilerplate from a single message content.

    Args:
        content: The message string.

    Returns:
        The stripped string if matched, else the original string.
    """
    match = BOILERPLATE_PATTERN.match(content)
    if match:
        new_content = content[match.end() :]
        if new_content.strip():
            return new_content
    return content


def strip_boilerplate(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Removes conversational boilerplate prefixes from assistant messages.

    Args:
        messages: List of conversation message dictionaries.

    Returns:
        The updated list of messages with boilerplate removed.
    """
    for msg in messages:
        if msg.get("role") == "assistant":
            msg["content"] = _strip_single_message(msg["content"])
    return messages


def apply_sliding_window(messages: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    """
    Applies a sliding window to keep only the most recent N messages, preserving the system prompt.

    Args:
        messages: List of conversation message dictionaries.
        limit: The maximum number of total messages to retain.

    Returns:
        The truncated list of messages.
    """
    if len(messages) <= limit:
        return messages

    sys_msg = [messages[0]] if messages[0].get("role") == "system" else []

    # We want to keep the system message + most recent (limit - len(sys_msg)) messages
    keep_count = limit - len(sys_msg)
    if keep_count <= 0:
        return sys_msg

    return sys_msg + messages[-keep_count:]


def compact_context(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Compacts the LLM context window by stripping boilerplate, enforcing the system prompt,
    and applying a sliding window size limit.

    Args:
        messages: List of conversation message dictionaries.

    Returns:
        The final compacted list of messages.
    """
    msgs_copy = copy.deepcopy(messages)

    # Ensure system prompt is at index 0
    if not msgs_copy or msgs_copy[0].get("role") != "system":
        msgs_copy.insert(0, SYSTEM_PROMPT.copy())
    else:
        msgs_copy[0] = SYSTEM_PROMPT.copy()

    msgs_copy = strip_boilerplate(msgs_copy)
    msgs_copy = apply_sliding_window(msgs_copy)
    return msgs_copy
