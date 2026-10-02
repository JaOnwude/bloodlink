"""User accounts and authentication identity."""

from uuid import UUID

from sqlalchemy import true
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column_type
from app.models.enums import UserRole


class User(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """A person who can sign in: a donor, a member of hospital staff, or an administrator.

    The account holds identity and credentials only. Role-specific information lives in
    dedicated tables (for example ``donors``) so that the authentication path stays
    narrow and the sensitive profile data can be protected independently.

    Attributes:
        email: Unique, case-normalised sign-in identifier.
        password_hash: Salted hash of the password. The plain password is never stored.
        role: Authorisation role that drives access control throughout the API.
        full_name: Display name.
        phone: Contact number in international format, used for alerts.
        is_active: Soft switch allowing an administrator to disable an account without
            deleting the history attached to it.
        hospital_id: For hospital staff, the facility they act on behalf of. Null for
            donors and administrators.
    """

    __tablename__ = "users"

    email: str = Field(max_length=320, unique=True, index=True)
    password_hash: str = Field(max_length=255)
    role: UserRole = Field(sa_type=enum_column_type(UserRole, "user_role"))
    full_name: str = Field(max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": true()})
    hospital_id: UUID | None = Field(
        default=None,
        foreign_key="hospitals.id",
        index=True,
        ondelete="SET NULL",
    )
