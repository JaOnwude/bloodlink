"""Account creation and credential checking.

Route handlers stay thin and delegate here, so the rules below can be tested and reused
(for example by the command-line script that creates administrators) without going
through HTTP.
"""

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.security import (
    hash_password,
    password_needs_rehash,
    perform_dummy_password_check,
    verify_password,
)
from app.models import User
from app.models.enums import UserRole


class EmailAlreadyRegisteredError(Exception):
    """Raised when an account already exists for the given email address."""


def get_user_by_email(session: Session, email: str) -> User | None:
    """Return the account with this (already normalised) email, or None."""
    return session.exec(select(User).where(User.email == email)).first()


def create_user(
    session: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
    phone: str | None = None,
) -> User:
    """Create and persist a new account.

    The password is hashed here; callers pass the plain value and must already have
    validated it against the password policy.

    Raises:
        EmailAlreadyRegisteredError: If the email is taken. This is detected both by a
            lookup and by the database's unique index, so two simultaneous registrations
            for the same email cannot both succeed.
    """
    if get_user_by_email(session, email) is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
        phone=phone,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise EmailAlreadyRegisteredError(email) from exc
    session.refresh(user)
    return user


def authenticate(session: Session, email: str, password: str) -> User | None:
    """Return the account for a correct email and password, otherwise None.

    A wrong password, an unknown email and a deactivated account all return None, so the
    caller can give one identical answer for every failure. Timing is kept similar too:
    when the email is unknown, a dummy password check runs so the response is not
    noticeably faster than for a real account.

    If the stored hash was made with weaker parameters than the current ones, it is
    upgraded now, while the correct plain password is available.
    """
    user = get_user_by_email(session, email)
    if user is None:
        perform_dummy_password_check(password)
        return None

    if not verify_password(password, user.password_hash):
        return None

    # The active check comes after the password check, so a deactivated account takes the
    # same time to reject as a wrong password.
    if not user.is_active:
        return None

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user
