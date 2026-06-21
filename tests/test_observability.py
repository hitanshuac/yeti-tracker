"""
Unit tests for the centralized error observability module.

Tests log_error() for schema validation, atomic writes, post-write
verification, guard clauses, and fixture compatibility.
"""

import json

import pytest

from src.observability import ErrorLogEntry, log_error


class TestLogError:
    """Tests for the schema-validated error logging function."""

    def test_log_error_creates_file(self, tmp_error_log: str) -> None:
        """log_error should create the file if it doesn't exist."""
        log_error("TestError", "test_component", "Test message", log_file=tmp_error_log)

        with open(tmp_error_log, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["error_type"] == "TestError"
        assert data[0]["component"] == "test_component"

    def test_log_error_appends_idempotently(self, tmp_error_log: str) -> None:
        """Multiple calls should append without data loss."""
        log_error("Error1", "comp1", "msg1", log_file=tmp_error_log)
        log_error("Error2", "comp2", "msg2", log_file=tmp_error_log)

        with open(tmp_error_log, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) == 2
        assert data[0]["error_type"] == "Error1"
        assert data[1]["error_type"] == "Error2"

    def test_log_error_preserves_existing_entries(
        self, canonical_error_log: str
    ) -> None:
        """Appending to a pre-populated log must preserve existing entries."""
        log_error("NewError", "new_comp", "new_msg", log_file=canonical_error_log)

        with open(canonical_error_log, encoding="utf-8") as f:
            data = json.load(f)
        # Original fixture had 1 entry, now should have 2
        assert len(data) == 2
        assert data[0]["error_type"] == "TestError"  # Original preserved
        assert data[1]["error_type"] == "NewError"  # New appended

    def test_log_error_validates_schema(self, tmp_error_log: str) -> None:
        """All entries must conform to the ErrorLogEntry Pydantic schema."""
        log_error("SchemaTest", "validator", "Testing schema", log_file=tmp_error_log)

        with open(tmp_error_log, encoding="utf-8") as f:
            data = json.load(f)

        # Must not raise ValidationError
        entry = ErrorLogEntry.model_validate(data[0])
        assert entry.error_type == "SchemaTest"
        assert entry.status == "UNRESOLVED"

    def test_log_error_includes_timestamp(self, tmp_error_log: str) -> None:
        """Each entry must have a numeric timestamp."""
        log_error("TimeTest", "timer", "Testing timestamp", log_file=tmp_error_log)

        with open(tmp_error_log, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data[0]["timestamp"], float)
        assert data[0]["timestamp"] > 0

    def test_guard_clause_empty_error_type(self, tmp_error_log: str) -> None:
        """Empty error_type must raise ValueError per defensive-programming.md Rule 4."""
        with pytest.raises(ValueError, match="error_type must be a non-empty string"):
            log_error("", "comp", "msg", log_file=tmp_error_log)

    def test_guard_clause_empty_component(self, tmp_error_log: str) -> None:
        """Empty component must raise ValueError per defensive-programming.md Rule 4."""
        with pytest.raises(ValueError, match="component must be a non-empty string"):
            log_error("Error", "", "msg", log_file=tmp_error_log)

    def test_fixture_schema_compatibility(self) -> None:
        """Verify the canonical fixture matches the ErrorLogEntry schema."""
        with open("tests/fixtures/error_logs_canonical.json", encoding="utf-8") as f:
            data = json.load(f)

        for entry in data:
            validated = ErrorLogEntry.model_validate(entry)
            assert validated.status == "UNRESOLVED"


class TestErrorLogEntryModel:
    """Tests for the ErrorLogEntry Pydantic schema."""

    def test_valid_entry(self) -> None:
        """A complete, valid entry should pass validation."""
        entry = ErrorLogEntry(
            timestamp=1700000000.0,
            error_type="TestError",
            component="test",
            message="Test message",
        )
        assert entry.status == "UNRESOLVED"
        assert entry.resolution_strategy is None

    def test_missing_required_field_raises(self) -> None:
        """Missing required fields should raise ValidationError."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ErrorLogEntry(
                error_type="Test", component="test"
            )  # missing timestamp, message
