"""Hospital registration, editing and administrative verification.

Every state change that matters is recorded in the audit log in the same transaction, so
the history of who registered, verified or rejected a facility, and when, is always
complete and consistent with the data.
"""

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import Hospital, User
from app.models.base import utcnow
from app.models.enums import VerificationStatus
from app.schemas.hospital import HospitalWrite
from app.services.audit import record_audit


class HospitalNotFoundError(Exception):
    """Raised when the requested hospital does not exist (or the user has none)."""


class AlreadyHasHospitalError(Exception):
    """Raised when a staff member who already belongs to a hospital tries to register one."""


class InvalidHospitalStateError(Exception):
    """Raised when an action is not allowed in the hospital's current verification state."""


def _snapshot(hospital: Hospital) -> dict[str, Any]:
    """JSON-friendly copy of the fields recorded in the audit log."""
    return {
        "name": hospital.name,
        "address": hospital.address,
        "city": hospital.city,
        "state": hospital.state,
        "latitude": hospital.latitude,
        "longitude": hospital.longitude,
        "registration_number": hospital.registration_number,
        "contact_phone": hospital.contact_phone,
        "verification_status": hospital.verification_status.value,
    }


def get_hospital_for_user(session: Session, user: User) -> Hospital | None:
    """Return the hospital the staff member belongs to, or None."""
    if user.hospital_id is None:
        return None
    return session.get(Hospital, user.hospital_id)


def _get_locked(session: Session, hospital_id: UUID) -> Hospital:
    """Load a hospital and lock its row until the transaction ends.

    Locking means two administrators acting on the same hospital at the same moment are
    handled one after the other, and the second sees the first one's result.
    """
    hospital = session.get(Hospital, hospital_id, with_for_update=True)
    if hospital is None:
        raise HospitalNotFoundError(str(hospital_id))
    return hospital


def register_hospital(
    session: Session, user: User, data: HospitalWrite, *, ip_address: str | None
) -> Hospital:
    """Create a hospital in the ``pending`` state and link the registering staff member to it.

    Raises:
        AlreadyHasHospitalError: If the user already belongs to a hospital.
    """
    if user.hospital_id is not None:
        raise AlreadyHasHospitalError(str(user.id))

    hospital = Hospital(**data.model_dump())
    session.add(hospital)
    user.hospital_id = hospital.id
    session.add(user)
    record_audit(
        session,
        actor=user,
        action="hospital.registered",
        entity_type="hospital",
        entity_id=hospital.id,
        after=_snapshot(hospital),
        ip_address=ip_address,
    )
    session.commit()
    session.refresh(hospital)
    return hospital


def update_hospital(
    session: Session, user: User, data: HospitalWrite, *, ip_address: str | None
) -> Hospital:
    """Replace the details of the staff member's hospital while it is not verified.

    A rejected hospital that is edited goes back to ``pending`` so an administrator
    reviews the corrected details. Verified hospitals cannot be edited here, because
    changing the name or location of a facility donors already trust must be reviewed.

    Raises:
        HospitalNotFoundError: If the user has no hospital.
        InvalidHospitalStateError: If the hospital is already verified.
    """
    if user.hospital_id is None:
        raise HospitalNotFoundError(str(user.id))
    hospital = _get_locked(session, user.hospital_id)

    if hospital.verification_status == VerificationStatus.VERIFIED:
        raise InvalidHospitalStateError(
            "A verified hospital cannot be edited. Contact an administrator to change its details."
        )

    before = _snapshot(hospital)
    for field, value in data.model_dump().items():
        setattr(hospital, field, value)

    resubmitted = hospital.verification_status == VerificationStatus.REJECTED
    if resubmitted:
        hospital.verification_status = VerificationStatus.PENDING
        hospital.rejection_reason = None

    session.add(hospital)
    record_audit(
        session,
        actor=user,
        action="hospital.resubmitted" if resubmitted else "hospital.updated",
        entity_type="hospital",
        entity_id=hospital.id,
        before=before,
        after=_snapshot(hospital),
        ip_address=ip_address,
    )
    session.commit()
    session.refresh(hospital)
    return hospital


def list_hospitals(
    session: Session,
    *,
    status: VerificationStatus | None,
    limit: int,
    offset: int,
) -> tuple[Sequence[Hospital], int]:
    """Return one page of hospitals (oldest first) and the total number that match.

    Args:
        status: Only hospitals in this state, or all hospitals when None.
        limit: Page size.
        offset: Number of hospitals to skip.
    """
    filters = [] if status is None else [Hospital.verification_status == status]
    total = session.exec(select(func.count()).select_from(Hospital).where(*filters)).one()
    items = session.exec(
        select(Hospital)
        .where(*filters)
        .order_by(col(Hospital.created_at), col(Hospital.id))
        .limit(limit)
        .offset(offset)
    ).all()
    return items, total


def get_hospital(session: Session, hospital_id: UUID) -> Hospital:
    """Return a hospital by id.

    Raises:
        HospitalNotFoundError: If there is no such hospital.
    """
    hospital = session.get(Hospital, hospital_id)
    if hospital is None:
        raise HospitalNotFoundError(str(hospital_id))
    return hospital


def get_staff_by_hospital(
    session: Session, hospital_ids: Sequence[UUID]
) -> dict[UUID, list[User]]:
    """Return the staff accounts linked to each of the given hospitals, in one query."""
    if not hospital_ids:
        return {}
    users = session.exec(
        select(User).where(col(User.hospital_id).in_(hospital_ids)).order_by(col(User.created_at))
    ).all()
    grouped: dict[UUID, list[User]] = {hospital_id: [] for hospital_id in hospital_ids}
    for user in users:
        if user.hospital_id is not None:
            grouped[user.hospital_id].append(user)
    return grouped


def verify_hospital(
    session: Session, admin: User, hospital_id: UUID, *, ip_address: str | None
) -> Hospital:
    """Mark a hospital as verified so it may raise blood requests.

    Raises:
        HospitalNotFoundError: If there is no such hospital.
        InvalidHospitalStateError: If it is already verified.
    """
    hospital = _get_locked(session, hospital_id)
    if hospital.verification_status == VerificationStatus.VERIFIED:
        raise InvalidHospitalStateError("This hospital is already verified.")

    before = {"verification_status": hospital.verification_status.value}
    hospital.verification_status = VerificationStatus.VERIFIED
    hospital.verified_at = utcnow()
    hospital.rejection_reason = None
    session.add(hospital)
    record_audit(
        session,
        actor=admin,
        action="hospital.verified",
        entity_type="hospital",
        entity_id=hospital.id,
        before=before,
        after={"verification_status": hospital.verification_status.value},
        ip_address=ip_address,
    )
    session.commit()
    session.refresh(hospital)
    return hospital


def reject_hospital(
    session: Session,
    admin: User,
    hospital_id: UUID,
    *,
    reason: str,
    ip_address: str | None,
) -> Hospital:
    """Reject a pending hospital, or revoke the verification of a verified one.

    The reason is shown to the hospital's staff so they can correct and resubmit.

    Raises:
        HospitalNotFoundError: If there is no such hospital.
        InvalidHospitalStateError: If it is already rejected.
    """
    hospital = _get_locked(session, hospital_id)
    if hospital.verification_status == VerificationStatus.REJECTED:
        raise InvalidHospitalStateError("This hospital is already rejected.")

    before = {"verification_status": hospital.verification_status.value}
    hospital.verification_status = VerificationStatus.REJECTED
    hospital.verified_at = None
    hospital.rejection_reason = reason
    session.add(hospital)
    record_audit(
        session,
        actor=admin,
        action="hospital.rejected",
        entity_type="hospital",
        entity_id=hospital.id,
        before=before,
        after={
            "verification_status": hospital.verification_status.value,
            "rejection_reason": reason,
        },
        ip_address=ip_address,
    )
    session.commit()
    session.refresh(hospital)
    return hospital
