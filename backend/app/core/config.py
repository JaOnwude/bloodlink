"""Application configuration.

All runtime settings are loaded from environment variables. During local development
they may also be supplied through a ``.env`` file located either in the backend folder
or in the repository root, so the same file can drive both Docker Compose and the API.

Settings are validated when the application starts: a misconfigured deployment fails
immediately with a clear message instead of misbehaving later at request time.
"""

from functools import lru_cache
from typing import Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Value used when no SECRET_KEY is provided. It is convenient for local development and
# automated tests, and is rejected outright when the environment is "production".
_INSECURE_DEFAULT_SECRET = "insecure-development-key-change-me"

# Minimum acceptable length for the signing key in production deployments.
_MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Typed, validated application settings.

    Attributes:
        app_name: Human-readable service name shown in the API documentation.
        environment: Deployment environment. Controls stricter production validation.
        api_prefix: URL prefix under which every API route is mounted.
        database_url: SQLAlchemy connection URL for PostgreSQL (psycopg 3 driver).
        secret_key: Key used to sign authentication tokens.
        access_token_expire_minutes: Lifetime of an issued access token and its cookie.
        auth_cookie_name: Name of the httpOnly cookie that carries the session token.
        auth_cookie_secure: Send the cookie over HTTPS only. Always on in production.
        auth_cookie_samesite: Cross-site policy of the cookie. ``lax`` stops browsers
            attaching it to cross-site form posts, which blocks cross-site request forgery.
        min_password_length: Shortest accepted password, counted in Unicode characters.
        max_password_length: Longest accepted password. Kept generous so passphrases and
            password-manager output are never rejected.
        login_max_failed_attempts: Failed sign-ins allowed per window before throttling.
        login_window_seconds: Length of the throttling window.
        cors_origins: Browser origins permitted to call the API with credentials.
        default_search_radius_km: Default radius used when searching for donors.
        min_donor_age_years: Lowest permitted donor age, in whole years.
        max_donor_age_years: Highest permitted donor age, in whole years.
        min_donor_weight_kg: Lowest permitted donor body weight.
        demo_password: Password shared by the demonstration accounts that the demo seed
            creates. Only the seeding command reads it; the API never does.
        demo_donor_phone: Optional phone number given to the first demonstration donor,
            so text-message alerts can be tried on a phone the developer owns.

    Note:
        The password limits follow NIST SP 800-63B-4: at least 15 characters when the
        password is the only authentication factor, support for at least 64 characters,
        and no character-composition rules.

        The donor age and weight limits are working defaults. They must be confirmed
        against the national transfusion service and WHO guidance cited in the project
        research notes before the system is used outside a demonstration.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "BloodLink API"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://bloodlink:change-me@localhost:5433/bloodlink"

    secret_key: str = _INSECURE_DEFAULT_SECRET
    access_token_expire_minutes: int = 60 * 12

    auth_cookie_name: str = "bloodlink_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    min_password_length: int = 15
    max_password_length: int = 128

    login_max_failed_attempts: int = 5
    login_window_seconds: int = 15 * 60

    cors_origins: list[str] = ["http://localhost:3000"]

    default_search_radius_km: float = 25.0
    min_donor_age_years: int = 18
    max_donor_age_years: int = 65
    min_donor_weight_kg: float = 50.0

    demo_password: str | None = None
    demo_donor_phone: str | None = None

    @property
    def session_cookie_secure(self) -> bool:
        """Whether the session cookie must be restricted to HTTPS.

        Production deployments always require it, regardless of the explicit setting, so a
        forgotten environment variable cannot weaken the cookie.
        """
        return self.auth_cookie_secure or self.environment == "production"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        """Normalise provider-style URLs so SQLAlchemy selects the psycopg 3 driver.

        Hosting platforms commonly hand out URLs beginning with ``postgres://`` or
        ``postgresql://``. SQLAlchemy would interpret those as the legacy psycopg2
        driver, which is not installed, so the scheme is rewritten transparently.
        """
        for legacy_scheme in ("postgres://", "postgresql://"):
            if value.startswith(legacy_scheme):
                return "postgresql+psycopg://" + value[len(legacy_scheme) :]
        return value

    @model_validator(mode="after")
    def _reject_insecure_secret_in_production(self) -> Self:
        """Refuse to start a production deployment with a weak or default signing key."""
        if self.environment == "production" and (
            self.secret_key == _INSECURE_DEFAULT_SECRET
            or len(self.secret_key) < _MIN_PRODUCTION_SECRET_LENGTH
        ):
            raise ValueError(
                "SECRET_KEY must be set to a random value of at least "
                f"{_MIN_PRODUCTION_SECRET_LENGTH} characters in production."
            )
        return self

    @model_validator(mode="after")
    def _require_secure_cookie_for_cross_site_policy(self) -> Self:
        """Browsers reject ``SameSite=None`` cookies that are not marked ``Secure``."""
        if self.auth_cookie_samesite == "none" and not self.session_cookie_secure:
            raise ValueError("AUTH_COOKIE_SAMESITE=none requires AUTH_COOKIE_SECURE=true.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance.

    The result is cached so environment parsing and validation happen exactly once.
    Tests that need different settings should construct ``Settings(...)`` directly.
    """
    return Settings()
