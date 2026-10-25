"""Families asking a verified hospital to find donors, and the hospital confirming them.

The flow keeps donors safe from fake appeals while giving families a real tool:

1. A family finds the hospital the patient is in, from a public page. Only verified
   hospitals are listed, ranked by how close their NIPOST postcode is to the one the family
   gives (the hospital's own, or the family's), or by distance from the family's position.
2. The family sends an appeal: the patient's group, what the doctor asked for, and the ward
   or lab reference. No account is needed, but the number of appeals one phone number can
   have waiting is capped, and the route limits how often one address can send.
3. The appeal waits at the hospital. Nobody is alerted yet.
4. Staff confirm the patient is on their ward and approve it. That raises an ordinary blood
   request through ``create_request``, with the same limits, audit trail and donor alerts
   as one the hospital typed in itself. Or they decline it, with a reason the family sees.

The family follows their appeal at a private link (its id), which shows its state and, once
approved, how many donors have pledged. It never shows any donor.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import BloodRequest, ComponentType, FamilyRequest, Hospital, User
from app.models.base import utcnow
from app.models.enums import FamilyRequestStatus, VerificationStatus
from app.schemas.family_request import FamilyRequestApprove, FamilyRequestCreate
from app.schemas.request import RequestCreate
from app.services.audit import record_audit
from app.services.distance import haversine_km
from app.services.postcode import POSTCODE_RINGS, parse_postcode, shared_ring
from app.services.requests import UnknownComponentError, create_request, expire_overdue

# Appeals one phone number may have waiting at once, across all hospitals.
MAX_PENDING_PER_PHONE = 2

# Hospitals returned by one search.
MAX_HOSPITALS_LISTED = 10


class FamilyRequestNotFoundError(Exception):
    """Raised when the appeal does not exist, or belongs to another hospital."""


class HospitalNotAvailableError(Exception):
    """Raised when an appeal is sent to a hospital that does not exist or is not verified."""


class TooManyPendingError(Exception):
    """Raised when a phone number already has the most appeals allowed waiting."""


class AlreadyDecidedError(Exception):
    """Raised when staff act on an appeal that was already approved or declined."""


@dataclass(frozen=True)
class HospitalResult:
    """A verified hospital found for a family, and how close it is."""

    hospital: Hospital
    distance_km: float | None
    postcode_ring: str | None


def _ring_rank(ring: str | None) -> int:
    return POSTCODE_RINGS.index(ring) if ring is not None else len(POSTCODE_RINGS)


def find_hospitals(
    session: Session,
    *,
    latitude: float | None,
    longitude: float | None,
    postcode: str | None,
    limit: int = MAX_HOSPITALS_LISTED,
) -> list[HospitalResult]:
    """List verified hospitals, closest first.

    With a postcode, the hospital with exactly that postcode comes first, then hospitals
    sharing its area, district, LGA and state. With a position, distance orders hospitals
    within each of those groups (or all of them, when no postcode is given). With neither,
    hospitals are listed by name.

    Postcodes are compared segment by segment, without calling NIPOST: every hospital's
    postcode was checked with NIPOST when it was saved.
    """
    segments = parse_postcode(postcode) if postcode else None
    hospitals = session.exec(
        select(Hospital).where(Hospital.verification_status == VerificationStatus.VERIFIED)
    ).all()

    results: list[HospitalResult] = []
    for hospital in hospitals:
        distance = (
            haversine_km(latitude, longitude, hospital.latitude, hospital.longitude)
            if latitude is not None and longitude is not None
            else None
        )
        ring = shared_ring(hospital.postcode, segments.area_code) if segments else None
        results.append(HospitalResult(hospital=hospital, distance_km=distance, postcode_ring=ring))

    def sort_key(result: HospitalResult) -> tuple:
        exact = segments is not None and result.hospital.postcode == segments.postcode
        return (
            0 if exact else 1,
            _ring_rank(result.postcode_ring),
            result.distance_km if result.distance_km is not None else 0.0,
            result.hospital.name,
        )

    results.sort(key=sort_key)
    return results[:limit]


def create_family_request(
    session: Session, hospital_id: UUID, data: FamilyRequestCreate
) -> tuple[FamilyRequest, Hospital]:
    """Record a family's appeal to a verified hospital. Nobody is alerted.

    Raises:
        HospitalNotAvailableError: If the hospital does not exist or is not verified.
        UnknownComponentError: If the component is not a known, active one.
        TooManyPendingError: If the phone number already has appeals waiting.
    """
    hospital = session.get(Hospital, hospital_id)
    if hospital is None or hospital.verification_status != VerificationStatus.VERIFIED:
        raise HospitalNotAvailableError(str(hospital_id))

    component = session.exec(
        select(ComponentType).where(
            ComponentType.code == data.component_code,
            col(ComponentType.is_active).is_(True),
        )
    ).first()
    if component is None:
        raise UnknownComponentError(data.component_code)

    waiting = session.exec(
        select(func.count())
        .select_from(FamilyRequest)
        .where(
            FamilyRequest.requester_phone == data.requester_phone,
            FamilyRequest.status == FamilyRequestStatus.PENDING,
        )
    ).one()
    if waiting >= MAX_PENDING_PER_PHONE:
        raise TooManyPendingError(data.requester_phone)

    appeal = FamilyRequest(
        hospital_id=hospital.id,
        requester_name=data.requester_name,
        requester_phone=data.requester_phone,
        recipient_group=data.recipient_group,
        component_type_id=component.id,
        units_needed=data.units_needed,
        ward_reference=data.ward_reference,
        notes=data.notes or None,
    )
    session.add(appeal)
    session.commit()
    session.refresh(appeal)
    return appeal, hospital


def get_family_request(session: Session, appeal_id: UUID) -> FamilyRequest:
    """Return an appeal by id.

    Raises:
        FamilyRequestNotFoundError: If there is none.
    """
    appeal = session.get(FamilyRequest, appeal_id)
    if appeal is None:
        raise FamilyRequestNotFoundError(str(appeal_id))
    return appeal


def list_for_hospital(
    session: Session, hospital_id: UUID, *, status: FamilyRequestStatus | None
) -> Sequence[FamilyRequest]:
    """The hospital's appeals, waiting ones first, then newest first."""
    query = select(FamilyRequest).where(FamilyRequest.hospital_id == hospital_id)
    if status is not None:
        query = query.where(FamilyRequest.status == status)
    appeals = session.exec(query.order_by(col(FamilyRequest.created_at).desc())).all()
    return sorted(appeals, key=lambda appeal: appeal.status != FamilyRequestStatus.PENDING)


def _locked_pending(session: Session, hospital_id: UUID, appeal_id: UUID) -> FamilyRequest:
    """Load the hospital's appeal, lock it, and check nobody has decided it yet.

    The lock means two staff acting at the same moment are handled one after the other, and
    the second is told it was already decided.
    """
    appeal = session.get(FamilyRequest, appeal_id, with_for_update=True)
    if appeal is None or appeal.hospital_id != hospital_id:
        raise FamilyRequestNotFoundError(str(appeal_id))
    if appeal.status != FamilyRequestStatus.PENDING:
        raise AlreadyDecidedError(str(appeal_id))
    return appeal


def approve_family_request(
    session: Session,
    staff: User,
    hospital: Hospital,
    appeal_id: UUID,
    data: FamilyRequestApprove,
    *,
    ip_address: str | None,
) -> tuple[FamilyRequest, BloodRequest]:
    """Confirm an appeal and raise a blood request from it.

    The request is raised through ``create_request``, so the hospital's limits and audit
    trail apply exactly as for a request staff type in themselves. The caller sends the
    donor alerts, as it does for any new request.

    Raises:
        FamilyRequestNotFoundError: If the appeal is not this hospital's.
        AlreadyDecidedError: If it was already approved or declined.
        pydantic.ValidationError: If the deadline is not acceptable for a request.
        UnknownComponentError, TooManyOpenRequestsError: As ``create_request`` does.
    """
    # Settle overdue requests first: doing so may commit, which must not happen while the
    # appeal below is already marked as approved.
    expire_overdue(session, hospital_id=hospital.id)
    appeal = _locked_pending(session, hospital.id, appeal_id)
    component = session.get(ComponentType, appeal.component_type_id)
    assert component is not None

    reference = f"Family appeal. Ward or reference: {appeal.ward_reference}."
    request_data = RequestCreate(
        recipient_group=appeal.recipient_group,
        component_code=component.code,
        units_needed=data.units_needed or appeal.units_needed,
        standby_units=data.standby_units,
        urgency=data.urgency,
        deadline=data.deadline,
        notes=f"{data.notes} {reference}" if data.notes else reference,
    )

    # Decided in the same transaction that raises the request, so a second approval waiting
    # on the lock finds it already approved.
    appeal.status = FamilyRequestStatus.APPROVED
    appeal.decided_by = staff.id
    appeal.decided_at = utcnow()
    session.add(appeal)
    try:
        request = create_request(session, staff, hospital, request_data, ip_address=ip_address)
    except Exception:
        session.rollback()
        _reopen_if_left_approved(session, appeal_id)
        raise

    appeal.blood_request_id = request.id
    session.add(appeal)
    record_audit(
        session,
        actor=staff,
        action="family_request.approved",
        entity_type="family_request",
        entity_id=appeal.id,
        after={"blood_request_id": str(request.id), "status": appeal.status.value},
        ip_address=ip_address,
    )
    session.commit()
    session.refresh(appeal)
    return appeal, request


def _reopen_if_left_approved(session: Session, appeal_id: UUID) -> None:
    """Put an appeal back to waiting if it was saved as approved without a blood request.

    Only reachable if something committed between marking the appeal and raising the
    request; the appeal must not look approved when no donor will ever be alerted.
    """
    appeal = session.get(FamilyRequest, appeal_id)
    if (
        appeal is not None
        and appeal.status == FamilyRequestStatus.APPROVED
        and appeal.blood_request_id is None
    ):
        appeal.status = FamilyRequestStatus.PENDING
        appeal.decided_by = None
        appeal.decided_at = None
        session.add(appeal)
        session.commit()


def decline_family_request(
    session: Session,
    staff: User,
    hospital: Hospital,
    appeal_id: UUID,
    *,
    reason: str,
    ip_address: str | None,
) -> FamilyRequest:
    """Turn an appeal down, with a reason the family will see.

    Raises:
        FamilyRequestNotFoundError: If the appeal is not this hospital's.
        AlreadyDecidedError: If it was already approved or declined.
    """
    appeal = _locked_pending(session, hospital.id, appeal_id)
    appeal.status = FamilyRequestStatus.DECLINED
    appeal.decided_by = staff.id
    appeal.decided_at = utcnow()
    appeal.decline_reason = reason
    session.add(appeal)
    record_audit(
        session,
        actor=staff,
        action="family_request.declined",
        entity_type="family_request",
        entity_id=appeal.id,
        after={"status": appeal.status.value, "decline_reason": reason},
        ip_address=ip_address,
    )
    session.commit()
    session.refresh(appeal)
    return appeal


def compose_family_update(appeal: FamilyRequest, hospital: Hospital, link: str) -> str:
    """The text a family receives once the hospital has decided on their appeal."""
    if appeal.status == FamilyRequestStatus.APPROVED:
        return (
            f"BloodLink: {hospital.name} confirmed your request for {appeal.recipient_group.value} "
            f"blood. Nearby donors are being alerted now. Follow it at {link}"
        )
    return (
        f"BloodLink: {hospital.name} could not accept your request. Reason: "
        f"{appeal.decline_reason}. Call {hospital.contact_phone}. Details: {link}"
    )
