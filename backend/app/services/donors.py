"""Donor profile operations."""

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import Donor, User
from app.schemas.donor import DonorWrite
from app.services.postcode import parse_postcode


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

    The postcode is cut back to its area before it is stored, so the donor's building is
    never kept. It must already have been checked with NIPOST by the caller. When the
    postcode is left out of the request, the area saved before is kept.
    """
    values: dict[str, object] = data.model_dump(exclude={"postcode"})
    if "postcode" in data.model_fields_set:
        segments = parse_postcode(data.postcode) if data.postcode else None
        values["postcode_area"] = segments.area_code if segments else None

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
