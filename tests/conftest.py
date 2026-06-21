"""
Shared test fixtures for the Yeti-Tracker test suite.

Provides isolated DuckDB paths, sample error log fixtures, and
temporary directory management for schema-validated I/O tests.
"""

import json

import pytest


@pytest.fixture
def tmp_db_path(tmp_path):
    """Provide an isolated DuckDB file path for testing."""
    return str(tmp_path / "test.duckdb")


@pytest.fixture
def tmp_error_log(tmp_path):
    """Provide an isolated error log file path for testing."""
    return str(tmp_path / "error_logs.json")


@pytest.fixture
def canonical_error_log(tmp_path):
    """Create a canonical-schema error log fixture for I/O tests.

    Returns:
        Path to a pre-populated error log matching the production schema.
    """
    log_path = str(tmp_path / "error_logs.json")
    canonical_data = [
        {
            "timestamp": 1700000000.0,
            "error_type": "TestError",
            "component": "test_fixture",
            "message": "This is a canonical fixture entry.",
            "status": "UNRESOLVED",
            "resolution_strategy": None,
        }
    ]
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(canonical_data, f, indent=2)
    return log_path


@pytest.fixture
def empty_error_log(tmp_path):
    """Create an empty (but valid schema) error log fixture.

    Returns:
        Path to an empty JSON array error log.
    """
    log_path = str(tmp_path / "error_logs.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump([], f)
    return log_path
