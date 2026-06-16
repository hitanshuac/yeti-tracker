"""
Module for error observability and logging.
"""

import json
import os
import traceback
from datetime import datetime
from typing import Any


def log_error(error: Exception, component: str, error_logs_path: str = "data/error_logs.json") -> dict[str, Any]:
    """
    Logs an error safely to the canonical JSON array error log file.

    Args:
        error: The caught exception.
        component: The component where the error occurred.
        error_logs_path: Path to the error logs file.

    Returns:
        The generated log entry dictionary.
    """
    os.makedirs(os.path.dirname(error_logs_path), exist_ok=True)

    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "error_type": type(error).__name__,
        "component": component,
        "message": str(error),
        "stack_trace_summary": traceback.format_exc()[-500:],  # keep it compressed
        "status": "UNRESOLVED",
        "resolution_strategy": None,
    }

    try:
        with open(error_logs_path, encoding="utf-8") as f:
            logs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logs = []

    logs.append(log_entry)

    temp_path = f"{error_logs_path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)

    os.replace(temp_path, error_logs_path)
    return log_entry
