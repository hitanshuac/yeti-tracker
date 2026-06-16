"""
Module for validating incoming records and quarantining malformed data.
"""

import json
import os
from typing import Any

from pydantic import BaseModel, ValidationError


class TelemetryRecord(BaseModel):
    """Pydantic model representing a valid telemetry record."""

    id: int
    payload: str
    tier: str


def _parse_jsonl(content: str) -> list[dict[str, Any]]:
    """Helper to parse JSONL content."""
    return [json.loads(line) for line in content.splitlines() if line.strip().startswith("{")]


def _load_existing_quarantine(path: str) -> list[dict[str, Any]]:
    """Loads existing quarantine logs."""
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                content = f.read().strip()
                if content.startswith("["):
                    return json.loads(content)
                return _parse_jsonl(content)
        return []
    except (json.JSONDecodeError, OSError):
        return []


def validate_and_route(
    records_data: list[dict[str, Any]], quarantine_dir: str = "data"
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Validates a list of records against the TelemetryRecord schema.
    Valid records are returned as dictionaries.
    Invalid records are saved to a quarantine log and returned separately.

    Args:
        records_data: The list of raw record dictionaries to validate.
        quarantine_dir: The directory to store quarantine logs.

    Returns:
        A tuple of (valid_records, quarantined_records).
    """
    valid_records = []
    quarantined = []

    for data in records_data:
        try:
            record = TelemetryRecord(**data)
            valid_records.append(record.model_dump())
        except ValidationError as e:
            quarantined.append({"raw_data": data, "error": str(e)})

    if quarantined:
        os.makedirs(quarantine_dir, exist_ok=True)
        quarantine_path = os.path.join(quarantine_dir, "quarantine_dlq.json")

        # Defensive Programming Rule 3: Idempotent atomic array append
        existing_q = _load_existing_quarantine(quarantine_path)

        existing_q.extend(quarantined)

        temp_path = f"{quarantine_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(existing_q, f, indent=2)

        os.replace(temp_path, quarantine_path)

    return valid_records, quarantined
