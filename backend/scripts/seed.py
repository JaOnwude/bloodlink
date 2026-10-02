"""Command-line entry point that loads reference data.

Usage (from the ``backend`` directory):

    uv run python -m scripts.seed
"""

from sqlmodel import Session

from app.db.seed import seed_reference_data
from app.db.session import engine


def main() -> None:
    """Load reference data into the configured database and report what changed."""
    with Session(engine) as session:
        result = seed_reference_data(session)
    print(
        f"Reference data ready: {result['compatibility_pairs']} compatibility pairs and "
        f"{result['component_types']} component types added."
    )


if __name__ == "__main__":
    main()
