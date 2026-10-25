"""Command-line entry point that brings an existing demonstration up to date.

Usage (from the ``backend`` directory):

    uv run python -m scripts.refresh_demo

It gives the Abuja demonstration hospital and donors their sample postcodes, raises a fresh
request if none is open, and, when ``DEMO_DONOR_PHONE`` is set, gives that number to the
donor who comes first for the request, so a text-message alert can be seen. See
``app.db.demo_refresh`` for exactly what it changes. Only demonstration records are touched,
and a second run changes nothing.

Like the demonstration seed, it refuses a production database unless ``--allow-production``
is passed.
"""

import argparse
import sys

from pydantic import TypeAdapter, ValidationError
from sqlmodel import Session

from app.core.config import get_settings
from app.db.demo_refresh import DemoNotSeededError, refresh_demo_data
from app.db.session import engine
from app.schemas.common import OptionalPhone


def main() -> int:
    """Refresh the demonstration data and report what changed. Returns the exit code."""
    parser = argparse.ArgumentParser(description="Bring BloodLink demonstration data up to date.")
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Permit refreshing when ENVIRONMENT is production.",
    )
    args = parser.parse_args()

    settings = get_settings()
    if settings.environment == "production" and not args.allow_production:
        print(
            "Refusing to change a production database. Pass --allow-production if this "
            "deployment is meant to be a demonstration.",
            file=sys.stderr,
        )
        return 1

    try:
        phone = TypeAdapter(OptionalPhone).validate_python(settings.demo_donor_phone)
    except ValidationError:
        print("DEMO_DONOR_PHONE is not a valid phone number.", file=sys.stderr)
        return 1

    try:
        with Session(engine) as session:
            summary = refresh_demo_data(session, donor_phone=phone)
    except DemoNotSeededError:
        print(
            "No demonstration data found. Run: uv run python -m scripts.seed_demo",
            file=sys.stderr,
        )
        return 1

    print("Demonstration data refreshed:")
    print(f"  Hospital postcodes added   {summary.hospital_postcodes}")
    print(f"  Donor postcode areas added {summary.donor_postcodes}")
    print(f"  Overdue requests expired   {summary.expired}")
    print(f"  Fresh Abuja request raised {'yes' if summary.request_raised else 'no, one is open'}")
    if summary.phone_donor:
        print(f"  DEMO_DONOR_PHONE given to  {summary.phone_donor}")
    else:
        print("  No phone changed (DEMO_DONOR_PHONE is not set)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
