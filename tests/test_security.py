"""
Unit tests for the security sanitization module.

Tests sanitize_input() for HTML stripping, character escaping,
curly brace removal, truncation, and edge case handling.
"""

from src.security import sanitize_input


class TestSanitizeInput:
    """Tests for the CWE-74 compliant input sanitizer."""

    def test_basic_text_passes_through(self) -> None:
        """Normal text should pass through with minimal changes."""
        result = sanitize_input("Hello world")
        assert "Hello world" in result

    def test_html_tags_stripped(self) -> None:
        """HTML tags should be completely removed."""
        result = sanitize_input("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "</script>" not in result

    def test_curly_braces_removed(self) -> None:
        """Curly braces should be stripped to prevent template injection."""
        result = sanitize_input("test {injection} here")
        assert "{" not in result
        assert "}" not in result

    def test_truncation_at_max_length(self) -> None:
        """Input exceeding max_length should be truncated."""
        long_input = "a" * 1000
        result = sanitize_input(long_input, max_length=500)
        assert len(result) <= 500

    def test_custom_max_length(self) -> None:
        """Custom max_length should be respected."""
        result = sanitize_input("a" * 100, max_length=50)
        assert len(result) <= 50

    def test_empty_string_returns_empty(self) -> None:
        """Empty string should return empty string."""
        result = sanitize_input("")
        assert result == ""

    def test_non_string_returns_empty(self) -> None:
        """Non-string input should return empty string per guard clause."""
        result = sanitize_input(12345)
        assert result == ""

    def test_whitespace_trimmed(self) -> None:
        """Leading and trailing whitespace should be stripped."""
        result = sanitize_input("  hello  ")
        assert result == "hello"

    def test_angle_brackets_escaped(self) -> None:
        """Angle brackets should be HTML-escaped."""
        result = sanitize_input("a < b > c")
        # After html.escape, < becomes &lt; and > becomes &gt;
        assert "<" not in result or "&lt;" in result

    def test_realistic_confession_text(self) -> None:
        """Realistic user input should pass through safely."""
        confession = "I drove 30km to work today and ran the AC for 6 hours."
        result = sanitize_input(confession)
        assert "30km" in result
        assert "AC" in result
