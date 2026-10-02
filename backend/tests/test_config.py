"""Tests for settings validation."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_provider_style_database_urls_are_normalised() -> None:
    """Hosting platforms' postgres:// URLs are rewritten to use the psycopg 3 driver."""
    for raw in ("postgres://u:p@host/db", "postgresql://u:p@host/db"):
        settings = Settings(_env_file=None, database_url=raw)
        assert settings.database_url == "postgresql+psycopg://u:p@host/db"


def test_explicit_driver_is_left_unchanged() -> None:
    """A URL that already names a driver is not rewritten."""
    url = "postgresql+psycopg://u:p@host/db"
    assert Settings(_env_file=None, database_url=url).database_url == url


def test_production_rejects_the_default_secret() -> None:
    """A production deployment cannot start with the built-in development key."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")


def test_production_rejects_a_short_secret() -> None:
    """Short signing keys are refused in production."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", secret_key="too-short")


def test_production_accepts_a_long_random_secret() -> None:
    """A sufficiently long key is accepted in production."""
    settings = Settings(_env_file=None, environment="production", secret_key="x" * 48)
    assert settings.environment == "production"
