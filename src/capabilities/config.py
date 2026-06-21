"""
# pylint: disable=line-too-long,duplicate-code,missing-docstring,import-outside-toplevel,redefined-outer-name,no-else-raise,too-few-public-methods
Module for loading and validating application configuration.
"""

import os


class MissingConfigurationError(Exception):
    """Exception raised when required environment variables are missing."""


def load_settings() -> dict[str, str]:
    """
    Loads application settings from the environment.

    Raises:
        MissingConfigurationError: If API_KEY is missing.

    Returns:
        A dictionary containing the configuration settings.
    """
    api_key = os.getenv("API_KEY")
    if not api_key:
        raise MissingConfigurationError("API_KEY environment variable is required per 12-factor BYOK rules.")
    return {"api_key": api_key}
