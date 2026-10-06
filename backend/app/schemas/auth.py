"""Request and response models for the authentication endpoints."""

from typing import Annotated
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
)

from app.core.config import get_settings
from app.core.password_policy import PasswordPolicyError, validate_password
from app.models.enums import UserRole
from app.schemas.common import OptionalPhone

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
    phone: OptionalPhone = None
    role: UserRole

    @field_validator("role")
    @classmethod
    def _only_self_service_roles(cls, value: UserRole) -> UserRole:
        if value not in _SELF_SERVICE_ROLES:
            raise ValueError("Accounts of this type cannot be created through registration.")
        return value

    @field_validator("password")
    @classmethod
    def _enforce_password_policy(cls, value: str, info: ValidationInfo) -> str:
        """Apply the password policy, using the email name as context to reject.

        This is a field validator (not a whole-model one) so that a problem is reported
        against the ``password`` field and the form can show the message beside it. The email
        is declared first, so by now its cleaned value is available in ``info.data``.
        """
        settings = get_settings()
        context_terms = ["bloodlink"]
        email = info.data.get("email")
        if isinstance(email, str):
            context_terms.append(email.split("@")[0])
        try:
            validate_password(
                value,
                min_length=settings.min_password_length,
                max_length=settings.max_password_length,
                context_terms=context_terms,
            )
        except PasswordPolicyError as exc:
            raise ValueError(str(exc)) from exc
        return value


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
