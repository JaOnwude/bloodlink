"""Tests for the password policy. No database is needed."""

import pytest

from app.core.password_policy import PasswordPolicyError, validate_password

MIN_LENGTH = 15
MAX_LENGTH = 128


def check(password: str, context_terms: tuple[str, ...] = ()) -> None:
    validate_password(
        password, min_length=MIN_LENGTH, max_length=MAX_LENGTH, context_terms=context_terms
    )


def test_a_long_passphrase_is_accepted() -> None:
    check("correct horse battery staple")


def test_length_boundary_is_exact() -> None:
    check("a1b2c3d4e5f6g7h")  # 15 characters
    with pytest.raises(PasswordPolicyError):
        check("a1b2c3d4e5f6g7")  # 14 characters


def test_overlong_passwords_are_rejected() -> None:
    with pytest.raises(PasswordPolicyError):
        check("ab1" * 50)


def test_length_is_counted_in_unicode_characters() -> None:
    """Fifteen Greek letters are fifteen characters even though they take more bytes."""
    check("αβγδεζηθικλμνξο")


def test_no_character_composition_rules_are_imposed() -> None:
    """A long all-lowercase passphrase is fine; length matters, not symbols."""
    check("just some lowercase words here")


def test_common_passwords_are_rejected_regardless_of_case() -> None:
    with pytest.raises(PasswordPolicyError):
        check("PasswordPassword")


def test_low_variety_passwords_are_rejected() -> None:
    with pytest.raises(PasswordPolicyError):
        check("abababababababab")


def test_blank_passwords_are_rejected() -> None:
    with pytest.raises(PasswordPolicyError):
        check(" " * 20)


def test_context_terms_are_rejected_inside_the_password() -> None:
    with pytest.raises(PasswordPolicyError):
        check("ada.okafor-has-a-long-phrase", context_terms=("ada.okafor",))


def test_short_context_terms_are_ignored() -> None:
    """A three-letter fragment would reject good passwords by coincidence."""
    check("a long passphrase about cats", context_terms=("cat",))
