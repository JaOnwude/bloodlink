"""Field types shared by several request models."""

import re
from typing import Annotated

from pydantic import BeforeValidator

# International-style number: optional leading plus, then 7 to 15 digits (the E.164 maximum).
_PHONE_PATTERN = re.compile(r"^\+?\d{7,15}$")

# Characters people commonly type inside phone numbers that carry no meaning.
_PHONE_SEPARATORS = re.compile(r"[\s\-().]")


def _clean_phone(value: object, *, required: bool) -> object:
    """Strip separators from a phone number and check its shape.

    Blank input becomes None when the number is optional and an error when it is required.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValueError("Phone number is required.")
        return None
    if not isinstance(value, str):
        raise ValueError("Phone number must be text.")
    cleaned = _PHONE_SEPARATORS.sub("", value)
    if not _PHONE_PATTERN.fullmatch(cleaned):
        raise ValueError("Enter a valid phone number, for example +2348031234567.")
    return cleaned


def _optional_phone(value: object) -> object:
    return _clean_phone(value, required=False)


def _required_phone(value: object) -> object:
    return _clean_phone(value, required=True)


def blank_to_none(value: object) -> object:
    """Treat empty or whitespace-only text as 'not provided'."""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


# A phone number that may be omitted. Stored without spaces, dashes or brackets.
OptionalPhone = Annotated[str | None, BeforeValidator(_optional_phone)]

# A phone number that must be supplied.
RequiredPhone = Annotated[str, BeforeValidator(_required_phone)]
