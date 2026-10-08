"""Command-line tool that expires every open request whose deadline has passed.

Requests are also expired automatically whenever a hospital reads them, so this command is
not needed for correctness. It is useful to run periodically (for example from a scheduled
job) so that data seen by other parts of the system, such as the donor feed, is current.

Usage (from the ``backend`` directory):

    uv run python -m scripts.expire_requests
"""

from sqlmodel import Session

from app.db.session import engine
from app.services.requests import expire_overdue


def main() -> None:
    """Expire all overdue requests and report how many there were."""
    with Session(engine) as session:
        count = expire_overdue(session)
    print(f"Expired {count} overdue request(s).")


if __name__ == "__main__":
    main()
