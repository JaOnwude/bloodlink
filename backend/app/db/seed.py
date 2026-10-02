"""Idempotent loading of reference data.

Only data the application cannot function without is loaded here: the blood compatibility
chart and the donatable component types. Running the loader repeatedly is safe, and it
never overwrites values that an administrator has since adjusted in the database.
"""

from sqlmodel import Session, select

from app.data.reference_data import COMPONENT_TYPES, RED_CELL_COMPATIBILITY
from app.models import BloodCompatibility, ComponentType


def seed_reference_data(session: Session) -> dict[str, int]:
    """Insert any missing compatibility pairs and component types.

    Existing rows are left untouched, which makes the function safe to run on every
    deployment and preserves any corrections made directly in the database.

    Args:
        session: An open session. The function commits on success.

    Returns:
        A mapping reporting how many rows were inserted, keyed by
        ``compatibility_pairs`` and ``component_types``.
    """
    existing_pairs = set(
        session.exec(
            select(BloodCompatibility.recipient_group, BloodCompatibility.donor_group)
        ).all()
    )
    pairs_added = 0
    for recipient, donors in RED_CELL_COMPATIBILITY.items():
        for donor in donors:
            if (recipient, donor) not in existing_pairs:
                session.add(BloodCompatibility(recipient_group=recipient, donor_group=donor))
                pairs_added += 1

    existing_codes = set(session.exec(select(ComponentType.code)).all())
    components_added = 0
    for component in COMPONENT_TYPES:
        if component["code"] not in existing_codes:
            session.add(ComponentType(**component))
            components_added += 1

    session.commit()
    return {"compatibility_pairs": pairs_added, "component_types": components_added}
