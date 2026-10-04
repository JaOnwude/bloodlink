"""Tests for password hashing and access tokens.

These cover the behaviours the rest of the authentication system relies on, including the
ways tokens can be forged or misused. They need no database.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    ACCESS_TOKEN_USE,
    ALGORITHM,
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    password_needs_rehash,
    perform_dummy_password_check,
    verify_password,
)
from app.models.enums import UserRole

SECRET = "test-secret-key-that-is-at-least-32-characters-long"
OTHER_SECRET = "a-completely-different-secret-key-for-testing-1234"


@pytest.fixture
def settings() -> Settings:
    """Settings with a known signing secret and a one-hour token lifetime."""
    return Settings(_env_file=None, secret_key=SECRET, access_token_expire_minutes=60)


# ---------------------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------------------


def test_hash_is_argon2id_and_not_the_plain_password() -> None:
    password = "correct horse battery staple"
    hashed = hash_password(password)

    assert hashed.startswith("$argon2id$")
    assert password not in hashed


def test_correct_password_verifies() -> None:
    hashed = hash_password("S3cure-passw0rd!")
    assert verify_password("S3cure-passw0rd!", hashed) is True


def test_wrong_password_is_rejected() -> None:
    hashed = hash_password("S3cure-passw0rd!")
    assert verify_password("s3cure-passw0rd!", hashed) is False


def test_same_password_hashes_differently_each_time() -> None:
    """A random salt per hash means identical passwords never share a stored value."""
    assert hash_password("same-password") != hash_password("same-password")


def test_unicode_passwords_round_trip() -> None:
    password = "pässwörd-密码-🔒"
    assert verify_password(password, hash_password(password)) is True


@pytest.mark.parametrize("bad_hash", ["", "not-a-hash", "$argon2id$garbage"])
def test_malformed_hashes_return_false_instead_of_raising(bad_hash: str) -> None:
    assert verify_password("anything", bad_hash) is False


def test_fresh_hash_does_not_need_rehash() -> None:
    assert password_needs_rehash(hash_password("a-password")) is False


def test_dummy_check_runs_without_error() -> None:
    assert perform_dummy_password_check("whatever") is None


# ---------------------------------------------------------------------------------------
# Access tokens
# ---------------------------------------------------------------------------------------


def test_token_round_trip_preserves_identity_and_role(settings: Settings) -> None:
    user_id = uuid4()
    token = create_access_token(user_id, UserRole.HOSPITAL_STAFF, settings=settings)

    claims = decode_access_token(token, settings=settings)

    assert claims.user_id == user_id
    assert claims.role is UserRole.HOSPITAL_STAFF


def test_token_lifetime_follows_the_configured_setting(settings: Settings) -> None:
    token = create_access_token(uuid4(), UserRole.DONOR, settings=settings)

    claims = decode_access_token(token, settings=settings)
    lifetime = claims.expires_at - claims.issued_at

    assert timedelta(minutes=59) <= lifetime <= timedelta(minutes=61)


def test_expired_token_is_rejected(settings: Settings) -> None:
    token = create_access_token(
        uuid4(), UserRole.DONOR, expires_delta=timedelta(seconds=-5), settings=settings
    )
    with pytest.raises(TokenError):
        decode_access_token(token, settings=settings)


def test_token_signed_with_another_secret_is_rejected(settings: Settings) -> None:
    other = Settings(_env_file=None, secret_key=OTHER_SECRET)
    token = create_access_token(uuid4(), UserRole.ADMIN, settings=other)

    with pytest.raises(TokenError):
        decode_access_token(token, settings=settings)


def test_tampered_payload_is_rejected(settings: Settings) -> None:
    """Swapping in another token's payload while keeping the signature must fail."""
    donor_token = create_access_token(uuid4(), UserRole.DONOR, settings=settings)
    admin_token = create_access_token(uuid4(), UserRole.ADMIN, settings=settings)

    header, admin_payload, _ = admin_token.split(".")
    _, _, donor_signature = donor_token.split(".")
    forged = ".".join([header, admin_payload, donor_signature])

    with pytest.raises(TokenError):
        decode_access_token(forged, settings=settings)


def test_unsigned_token_with_alg_none_is_rejected(settings: Settings) -> None:
    """The classic downgrade attack: a token that claims to need no signature."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid4()),
        "role": UserRole.ADMIN.value,
        "token_use": ACCESS_TOKEN_USE,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    unsigned = jwt.encode(payload, None, algorithm="none")

    with pytest.raises(TokenError):
        decode_access_token(unsigned, settings=settings)


def test_token_issued_for_another_purpose_is_rejected(settings: Settings) -> None:
    """A correctly signed token that is not a session token cannot be used to sign in."""
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": UserRole.DONOR.value,
            "token_use": "password_reset",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        SECRET,
        algorithm=ALGORITHM,
    )

    with pytest.raises(TokenError):
        decode_access_token(token, settings=settings)


def test_token_with_unknown_role_is_rejected(settings: Settings) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "role": "superuser",
            "token_use": ACCESS_TOKEN_USE,
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        SECRET,
        algorithm=ALGORITHM,
    )

    with pytest.raises(TokenError):
        decode_access_token(token, settings=settings)


@pytest.mark.parametrize("garbage", ["", "not.a.token", "abc", "a.b.c.d"])
def test_garbage_input_is_rejected(garbage: str, settings: Settings) -> None:
    with pytest.raises(TokenError):
        decode_access_token(garbage, settings=settings)
