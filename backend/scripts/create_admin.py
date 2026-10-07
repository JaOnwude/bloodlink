"""Command-line tool that creates an administrator account.

Administrators cannot register themselves through the API. They are created by someone
with access to the server, using this script:

    uv run python -m scripts.create_admin --email you@example.com --name "Your Name"

The password is read from the terminal without echo, so it never appears on screen or in
the shell history.
"""

import argparse
import getpass
import sys

from pydantic import TypeAdapter, ValidationError
from sqlmodel import Session

from app.core.config import get_settings
from app.core.password_policy import PasswordPolicyError, validate_password
from app.db.session import engine
from app.models.enums import UserRole
from app.schemas.auth import NormalisedEmail
from app.services.auth import EmailAlreadyRegisteredError, create_user


def main() -> int:
    """Create the administrator and report the outcome. Returns the process exit code."""
    parser = argparse.ArgumentParser(description="Create a BloodLink administrator account.")
    parser.add_argument("--email", required=True, help="Sign-in email address")
    parser.add_argument("--name", required=True, help="Full name")
    args = parser.parse_args()

    try:
        email = TypeAdapter(NormalisedEmail).validate_python(args.email)
    except ValidationError:
        print("That is not a valid email address.", file=sys.stderr)
        return 1

    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        print("The passwords do not match.", file=sys.stderr)
        return 1

    settings = get_settings()
    try:
        validate_password(
            password,
            min_length=settings.min_password_length,
            max_length=settings.max_password_length,
            context_terms=[email.split("@")[0], "bloodlink"],
        )
    except PasswordPolicyError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    with Session(engine) as session:
        try:
            user = create_user(
                session,
                email=email,
                password=password,
                full_name=args.name.strip(),
                role=UserRole.ADMIN,
            )
        except EmailAlreadyRegisteredError:
            print("An account with that email already exists.", file=sys.stderr)
            return 1

    print(f"Administrator created: {user.email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
