"""
RAG context retrieval using DuckDB keyword matching.

Searches the carbon_factors CSV for rows matching keywords from user text
and returns a formatted context string for LLM prompt injection.
"""

import json
import os
import re

import duckdb


def _build_rag_query(text: str, dataset_path: str) -> str | None:
    """Build a DuckDB LIKE query from extracted keywords.

    Args:
        text: User confession text.
        dataset_path: Path to the carbon factors CSV.

    Returns:
        SQL query string, or None if no usable keywords found.
    """
    words = re.findall(r"\w+", text.lower())
    keywords = [w for w in words if len(w) > 4]
    if not keywords:
        return None

    conditions = [f"LOWER(description) LIKE '%{kw}%' OR LOWER(activity) LIKE '%{kw}%'" for kw in keywords]
    where_clause = " OR ".join(conditions)
    return (
        f"SELECT activity, description, co2_kg_per_unit, social_cost_inr_per_kg "
        f"FROM read_csv_auto('{dataset_path}') "
        f"WHERE {where_clause} LIMIT 3"
    )


def fetch_rag_context(text: str, dataset_path: str = "data/carbon_factors.csv") -> str:
    """Use DuckDB to extract context rows from the emissions dataset.

    Args:
        text: The user's confession text to extract keywords from.
        dataset_path: Path to the carbon factors CSV.

    Returns:
        Formatted context string for LLM prompt, or empty string.
    """
    query = _build_rag_query(text, dataset_path)
    if not query:
        return ""

    try:
        conn = duckdb.connect()
        results = conn.execute(query).fetchall()
        conn.close()

        if not results:
            return ""

        context_lines = ["RAG CONTEXT (Carbon Factors from Database):"]
        for row in results:
            context_lines.append(f"- {row[0]} ({row[1]}): {row[2]} kg CO2/unit, ${row[3]} SCC/unit")
        return "\n".join(context_lines)
    except Exception as e:
        _log_rag_error(e)
        return ""


def _log_rag_error(error: Exception) -> None:
    """Minimal error logger for RAG service."""
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
            "error_type": type(error).__name__,
            "component": "rag_service",
            "message": str(error),
            "status": "UNRESOLVED",
            "resolution_strategy": None,
        }
    )

    temp_file = f"{log_file}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    os.replace(temp_file, log_file)
