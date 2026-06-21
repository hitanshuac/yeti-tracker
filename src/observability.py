"""
# pylint: disable=line-too-long,duplicate-code,missing-docstring,import-outside-toplevel,redefined-outer-name,no-else-raise,too-few-public-methods
Centralized error observability layer.

Enforces defensive programming standards with schema-validated file I/O operations.
"""

import json
import os
import time

from pydantic import BaseModel, ValidationError


class ErrorLogEntry(BaseModel):
    """Schema for error log entries."""

    timestamp: float
    error_type: str
    component: str
    message: str
    status: str = "UNRESOLVED"
    resolution_strategy: str | None = None


def _validate_log_inputs(error_type: str, component: str) -> None:
    if not error_type or not isinstance(error_type, str):
        raise ValueError(f"error_type must be a non-empty string, got: {error_type!r}")
    if not component or not isinstance(component, str):
        raise ValueError(f"component must be a non-empty string, got: {component!r}")


def _load_existing_logs(log_file: str) -> list[ErrorLogEntry]:
    logs: list[ErrorLogEntry] = []
    if os.path.exists(log_file):
        with open(log_file, encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError(
                        f"Schema mismatch: Expected list, got {type(data).__name__}"
                    )
                logs = [ErrorLogEntry.model_validate(item) for item in data]
            except (json.JSONDecodeError, ValidationError) as e:
                raise ValueError(f"Schema mismatch in {log_file}: {e}") from e
    return logs


def log_error(
    error_type: str,
    component: str,
    message: str,
    log_file: str = "data/error_logs.json",
) -> None:
    """Log an error to the JSON file with atomic writes and schema validation.

    Args:
        error_type: The exception class name or error type.
        component: The module where the error occurred.
        message: The detailed error message.
        log_file: Path to the JSON log file.

    Raises:
        ValueError: If input parameters are invalid or schema mismatch occurs.
        RuntimeError: If data corruption is detected post-write.
    """
    _validate_log_inputs(error_type, component)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    logs = _load_existing_logs(log_file)

    before_len = len(logs)

    new_entry = ErrorLogEntry(
        timestamp=time.time(),
        error_type=error_type,
        component=component,
        message=message,
    )
    logs.append(new_entry)

    temp_file = f"{log_file}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump([log.model_dump() for log in logs], f, indent=2)

    os.replace(temp_file, log_file)

    # Post-write verification (idempotent file operations rule)
    with open(log_file, encoding="utf-8") as f:
        verified_data = json.load(f)
        if len(verified_data) < before_len + 1:
            raise RuntimeError("Data corruption during error log append")
