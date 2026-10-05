"""Donor profile operations."""

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import Donor, User
from app.schemas.donor import DonorWrite


def get_donor_for_user(session: Session, user: User) -> Donor | None:
    """Return the donor profile that belongs to ``user``, or None if none exists yet."""
    return session.exec(select(Donor).where(Donor.user_id == user.id)).first()


def save_donor_profile(session: Session, user: User, data: DonorWrite) -> tuple[Donor, bool]:
    """Create the user's donor profile, or replace it if one already exists.

    Returns:
        The saved profile and a flag that is True when it was newly created.

    If two first-time saves for the same user arrive at once, the database's unique
    constraint rejects the second insert; it is then retried as an update instead of
    failing.
    """
    values = data.model_dump()

    donor = get_donor_for_user(session, user)
    if donor is None:
        donor = Donor(user_id=user.id, **values)
        session.add(donor)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = get_donor_for_user(session, user)
            if existing is None:
                raise
            return _apply_update(session, existing, values), False
        session.refresh(donor)
        return donor, True

    return _apply_update(session, donor, values), False


def _apply_update(session: Session, donor: Donor, values: dict[str, object]) -> Donor:
    for field, value in values.items():
        setattr(donor, field, value)
    session.add(donor)
    session.commit()
    session.refresh(donor)
    return donor


def set_availability(session: Session, donor: Donor, *, is_available: bool) -> Donor:
    """Turn alerts on or off for a donor."""
    donor.is_available = is_available
    session.add(donor)
    session.commit()
    session.refresh(donor)
    return donor
