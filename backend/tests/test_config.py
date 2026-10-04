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


def test_session_cookie_is_always_secure_in_production() -> None:
    """Production forces the Secure flag even when it was not requested explicitly."""
    settings = Settings(
        _env_file=None, environment="production", secret_key="x" * 48, auth_cookie_secure=False
    )
    assert settings.session_cookie_secure is True


def test_session_cookie_follows_the_setting_in_development() -> None:
    """Local development over plain HTTP works without the Secure flag."""
    assert Settings(_env_file=None).session_cookie_secure is False
    assert Settings(_env_file=None, auth_cookie_secure=True).session_cookie_secure is True


def test_samesite_none_requires_a_secure_cookie() -> None:
    """Browsers discard SameSite=None cookies that are not Secure, so refuse the setting."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, auth_cookie_samesite="none")
    ok = Settings(_env_file=None, auth_cookie_samesite="none", auth_cookie_secure=True)
    assert ok.auth_cookie_samesite == "none"


def test_password_limits_follow_current_guidance() -> None:
    """Defaults: 15 characters minimum, and room for passphrases of 64 or more."""
    settings = Settings(_env_file=None)
    assert settings.min_password_length == 15
    assert settings.max_password_length >= 64
