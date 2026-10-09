"""Command-line entry point that loads the demonstration data.

Usage (from the ``backend`` directory, with ``DEMO_PASSWORD`` set in ``.env``):

    uv run python -m scripts.seed_demo

Every demonstration account signs in with the ``DEMO_PASSWORD`` value. It is checked
against the same password policy as any other account. Set ``DEMO_DONOR_PHONE`` as well to
give the first demonstration donor your own number, so you can receive test alerts.

Seeding a production database is refused unless ``--allow-production`` is passed, so the
demonstration accounts can only reach a live deployment on purpose, for example a hosted
demonstration of the capstone.
"""

import argparse
import sys

from pydantic import TypeAdapter, ValidationError
from sqlmodel import Session

from app.core.config import get_settings
from app.core.password_policy import PasswordPolicyError, validate_password
from app.db.demo_seed import ADMIN_EMAIL, DEMO_DOMAIN, donor_email, seed_demo_data, staff_email
from app.db.session import engine
from app.schemas.common import OptionalPhone


def main() -> int:
    """Load the demonstration data and list the accounts. Returns the process exit code."""
    parser = argparse.ArgumentParser(description="Load BloodLink demonstration data.")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Permit seeding when ENVIRONMENT is production.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if settings.environment == "production" and not args.allow_production:
        print(
            "Refusing to seed a production database. Pass --allow-production if this "
            "deployment is meant to be a demonstration.",
            file=sys.stderr,
        )
        return 1

    password = settings.demo_password
    if not password:
        print("Set DEMO_PASSWORD in .env first (see .env.example).", file=sys.stderr)
        return 1
    try:
        validate_password(
            password,
            min_length=settings.min_password_length,
            max_length=settings.max_password_length,
            context_terms=["bloodlink", "demo"],
        )
    except PasswordPolicyError as exc:
        print(f"DEMO_PASSWORD is not acceptable: {exc}", file=sys.stderr)
        return 1

    try:
        phone = TypeAdapter(OptionalPhone).validate_python(settings.demo_donor_phone)
    except ValidationError:
        print("DEMO_DONOR_PHONE is not a valid phone number.", file=sys.stderr)
        return 1

    with Session(engine) as session:
        summary = seed_demo_data(session, password=password, donor_phone=phone)

    def plural(count: int, word: str) -> str:
        return f"{count} {word}" if count == 1 else f"{count} {word}s"

    if not summary.created:
        print("Demonstration data is already present; nothing was changed.")
    else:
        print(
            f"Demonstration data loaded: {plural(summary.users, 'account')}, "
            f"{plural(summary.hospitals, 'hospital')}, {plural(summary.donors, 'donor')}, "
            f"{plural(summary.requests, 'request')}, {plural(summary.pledges, 'pledge')} "
            f"and {plural(summary.donations, 'donation')}."
        )
    print(f"\nSign in with any of these, using the DEMO_PASSWORD value (all @{DEMO_DOMAIN}):")
    print(f"  Administrator          {ADMIN_EMAIL}")
    print(f"  Lagos hospital staff   {staff_email('lagos')}")
    print(f"  Abuja hospital staff   {staff_email('abuja')}")
    print(f"  Enugu hospital staff   {staff_email('enugu')}")
    print(f"  Pending hospital staff {staff_email('pending')}")
    print(f"  Donor (O-, Lagos)      {donor_email(1)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
