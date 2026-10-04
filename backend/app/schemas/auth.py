"""Request and response models for the authentication endpoints."""

import re
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.config import get_settings
from app.core.password_policy import PasswordPolicyError, validate_password
from app.models.enums import UserRole

# International-style number: optional leading plus, then 7 to 15 digits (the E.164 maximum).
_PHONE_PATTERN = re.compile(r"^\+?\d{7,15}$")

# Characters people commonly type inside phone numbers that carry no meaning.
_PHONE_SEPARATORS = re.compile(r"[\s\-().]")

# Roles that a visitor may choose for themselves. Administrators are never self-registered;
# they are created from the command line by someone with access to the server.
_SELF_SERVICE_ROLES = {UserRole.DONOR, UserRole.HOSPITAL_STAFF}


def _strip_whitespace(value: object) -> object:
    """Trim surrounding whitespace from strings and leave every other value untouched."""
    return value.strip() if isinstance(value, str) else value


# Email addresses are compared and stored in lower case, so "Ada@Example.com" and
# "ada@example.com" are the same account and cannot be registered twice.
NormalisedEmail = Annotated[
    EmailStr,
    BeforeValidator(_strip_whitespace),
    AfterValidator(str.lower),
]


class RegisterRequest(BaseModel):
    """Details a visitor supplies to create an account.

    Attributes:
        email: Sign-in identifier; trimmed and lower-cased.
        password: The chosen password, checked against the password policy.
        full_name: Display name.
        phone: Optional contact number; separators are removed.
        role: ``donor`` or ``hospital_staff``. Administrator accounts cannot be requested.
    """

    email: NormalisedEmail
    # The hard cap only protects the server from absurdly large payloads. The real length
    # limits come from the password policy so users get a precise, readable message.
    password: str = Field(min_length=1, max_length=1024, repr=False)
    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)
    ]
    phone: str | None = None
    role: UserRole

    @field_validator("role")
    @classmethod
    def _only_self_service_roles(cls, value: UserRole) -> UserRole:
        if value not in _SELF_SERVICE_ROLES:
            raise ValueError("Accounts of this type cannot be created through registration.")
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def _clean_phone(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if not isinstance(value, str):
            raise ValueError("Phone number must be text.")
        cleaned = _PHONE_SEPARATORS.sub("", value)
        if not _PHONE_PATTERN.fullmatch(cleaned):
            raise ValueError("Enter a valid phone number, for example +2348031234567.")
        return cleaned

    @model_validator(mode="after")
    def _enforce_password_policy(self) -> Self:
        """Apply the password policy, using the email name as context to reject."""
        settings = get_settings()
        try:
            validate_password(
                self.password,
                min_length=settings.min_password_length,
                max_length=settings.max_password_length,
                context_terms=[self.email.split("@")[0], "bloodlink"],
            )
        except PasswordPolicyError as exc:
            raise ValueError(str(exc)) from exc
        return self


class LoginRequest(BaseModel):
    """Credentials supplied to sign in.

    The password policy is intentionally not applied here: a person must always be able to
    sign in with the password they already have, even if the policy has since changed.
    """

    email: NormalisedEmail
    password: str = Field(min_length=1, max_length=1024, repr=False)


class UserRead(BaseModel):
    """The account details returned to the signed-in user.

    The password hash and other internal fields are never included.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: UserRole
    phone: str | None
    hospital_id: UUID | None
