"""Password hashing and signed access tokens.

This module is the only place in the application that knows how credentials are protected:

* Passwords are hashed with Argon2id, a memory-hard algorithm designed to make large-scale
  guessing attacks expensive. The plain password is never stored or logged.
* Sessions are represented by short-lived JSON Web Tokens signed with a server-side secret.
  The browser holds the token in an httpOnly cookie; the API verifies the signature and
  expiry on every request.

Keeping these concerns in one small, dependency-free module makes them easy to test in
isolation and easy to review, which matters because mistakes here are security defects.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import Settings, get_settings
from app.models.enums import UserRole

# The signing algorithm is a constant rather than a setting on purpose. If it were
# configurable, a misconfiguration (or an attacker-supplied token header) could downgrade
# verification to a weaker algorithm. Tokens are decoded with this single algorithm only.
ALGORITHM = "HS256"

# Value of the ``token_use`` claim on session tokens. Tokens issued for any other purpose
# carry a different value, so they can never be accepted as a login session.
ACCESS_TOKEN_USE = "access"

# One shared hasher. Its defaults follow the current Argon2 recommendations and embed the
# parameters in every hash, so parameters can be strengthened later without invalidating
# existing passwords (see ``password_needs_rehash``).
_hasher = PasswordHasher()


# ---------------------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Return a salted Argon2id hash of ``password``, suitable for storing in the database.

    A fresh random salt is generated for every call, so hashing the same password twice
    yields different strings. The salt and the algorithm parameters are embedded in the
    returned value, which is why no separate salt column is needed.

    Args:
        password: The plain-text password. Its strength is validated elsewhere, before
            this function is called.

    Returns:
        An encoded hash beginning with ``$argon2id$``.
    """
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plain-text password against a stored hash.

    Any failure to verify, including a hash that is malformed or empty, is reported as
    ``False`` rather than as an exception. Callers therefore handle a single outcome and
    cannot accidentally leak, through an unhandled error, whether an account exists.

    Args:
        password: The password supplied by the user.
        password_hash: The value previously produced by ``hash_password``.

    Returns:
        True only when the password matches the hash.
    """
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """Report whether a stored hash was made with weaker parameters than the current ones.

    After a successful login, the caller can use this to transparently upgrade the stored
    hash while the plain password is available, so security improves over time without
    forcing anyone to reset their password.
    """
    return _hasher.check_needs_rehash(password_hash)


@cache
def _dummy_hash() -> str:
    """Hash of a throwaway password, computed once on first use."""
    return _hasher.hash("bloodlink-timing-equalisation-password")


def perform_dummy_password_check(password: str) -> None:
    """Spend the same time as a real password check without matching any account.

    When someone signs in with an email address that has no account, the application would
    otherwise answer noticeably faster than for a real account, because there is no hash to
    verify. That timing difference lets an attacker discover which emails are registered.
    Calling this function in the "no such account" branch makes both paths take about the
    same time.

    The result is deliberately discarded.
    """
    verify_password(password, _dummy_hash())


# ---------------------------------------------------------------------------------------
# Access tokens
# ---------------------------------------------------------------------------------------


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, forged or not a session token.

    A single exception type is used for every cause on purpose. The reason a token was
    rejected is useful to developers in logs but must not be revealed to the caller, who
    only needs to know that they have to sign in again.
    """


@dataclass(frozen=True)
class AccessTokenClaims:
    """The verified contents of a session token.

    Attributes:
        user_id: The account the token was issued to.
        role: The role recorded at issue time. It is used for fast checks, and sensitive
            actions should still confirm it against the database.
        issued_at: When the token was created (UTC).
        expires_at: When the token stops being valid (UTC).
    """

    user_id: UUID
    role: UserRole
    issued_at: datetime
    expires_at: datetime


def create_access_token(
    user_id: UUID,
    role: UserRole,
    *,
    expires_delta: timedelta | None = None,
    settings: Settings | None = None,
) -> str:
    """Create a signed session token for a user.

    Args:
        user_id: Identifier of the authenticated account; stored as the standard ``sub``
            (subject) claim.
        role: The account's role at the time of issue.
        expires_delta: How long the token stays valid. Defaults to the configured
            ``access_token_expire_minutes``.
        settings: Settings to use instead of the process-wide ones. Intended for tests.

    Returns:
        The encoded token as a string.
    """
    config = settings or get_settings()
    now = datetime.now(UTC)
    lifetime = (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=config.access_token_expire_minutes)
    )
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "token_use": ACCESS_TOKEN_USE,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, config.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, *, settings: Settings | None = None) -> AccessTokenClaims:
    """Verify a session token and return its claims.

    Verification checks, in order: that the signature matches the server secret using the
    expected algorithm only; that the expiry, issue time and subject claims are present
    and the token has not expired; that the token was issued as a session token; and that
    the subject and role are well-formed.

    Args:
        token: The encoded token, typically read from the session cookie.
        settings: Settings to use instead of the process-wide ones. Intended for tests.

    Returns:
        The verified claims.

    Raises:
        TokenError: If the token fails any of the checks above.
    """
    config = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            config.secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid or expired token.") from exc

    if payload.get("token_use") != ACCESS_TOKEN_USE:
        raise TokenError("Token was not issued as a session token.")

    try:
        return AccessTokenClaims(
            user_id=UUID(payload["sub"]),
            role=UserRole(payload["role"]),
            issued_at=datetime.fromtimestamp(payload["iat"], UTC),
            expires_at=datetime.fromtimestamp(payload["exp"], UTC),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise TokenError("Token claims are malformed.") from exc
