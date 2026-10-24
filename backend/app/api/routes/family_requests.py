"""Families finding a verified hospital and asking it for blood, and staff answering them.

Two groups of routes:

* ``/public/...`` needs no account. A family lists verified hospitals, sends an appeal to
  one, and follows it at its private link. These routes never call NIPOST, so nobody can
  spend BloodLink's key through them, and sending is rate limited.
* ``/family-requests/...`` is for the staff of the hospital the appeal was sent to. They
  see the family's details to call back, then approve (raising a blood request, which
  alerts donors as usual) or decline with a reason.

The family is texted when their appeal is decided, after the response has gone out.
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import ValidationError
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

from app.api.deps import ClientIp, SessionDep, StaffUser, VerifiedHospital
from app.core.config import get_settings
from app.core.rate_limit import get_appeal_limiter
from app.models import BloodRequest, ComponentType, FamilyRequest, Hospital
from app.models.enums import FamilyRequestStatus
from app.schemas.common import OptionalPostcode
from app.schemas.family_request import (
    FamilyRequestApprove,
    FamilyRequestCreate,
    FamilyRequestCreated,
    FamilyRequestDecline,
    FamilyRequestRead,
    FamilyRequestTracking,
    PublicHospitalRead,
)
from app.schemas.request import RequestRead
from app.services.family_requests import (
    MAX_HOSPITALS_LISTED,
    AlreadyDecidedError,
    FamilyRequestNotFoundError,
    HospitalNotAvailableError,
    TooManyPendingError,
    approve_family_request,
    compose_family_update,
    create_family_request,
    decline_family_request,
    find_hospitals,
    get_family_request,
    list_for_hospital,
)
from app.services.notifications import alert_in_background
from app.services.requests import (
    TooManyOpenRequestsError,
    UnknownComponentError,
    build_reads,
)
from app.services.sms import get_sms_sender, mask_phone

logger = logging.getLogger("bloodlink.family_requests")

public_router = APIRouter(prefix="/public", tags=["families"])
router = APIRouter(prefix="/family-requests", tags=["families"])

_NOT_FOUND = "This request was not found."


def tracking_link(appeal_id: UUID) -> str:
    """The private page where a family follows their appeal."""
    return f"{get_settings().frontend_url.rstrip('/')}/find-blood/{appeal_id}"


def _notify_family_in_background(engine: Engine, appeal_id: UUID) -> None:
    """Text the family that their appeal was decided. Never raises."""
    try:
        with Session(engine) as session:
            appeal = session.get(FamilyRequest, appeal_id)
            hospital = session.get(Hospital, appeal.hospital_id) if appeal else None
            if appeal is None or hospital is None:
                return
            text = compose_family_update(appeal, hospital, tracking_link(appeal.id))
            result = get_sms_sender().send(appeal.requester_phone, text)
        if not result.ok:
            logger.warning(
                "Could not text family %s: %s", mask_phone(appeal.requester_phone), result.error
            )
    except Exception:
        logger.exception("Texting the family about appeal %s failed", appeal_id)


def _component_names(session: Session, appeals: list[FamilyRequest]) -> dict[UUID, ComponentType]:
    ids = {appeal.component_type_id for appeal in appeals}
    if not ids:
        return {}
    components = session.exec(select(ComponentType).where(col(ComponentType.id).in_(ids))).all()
    return {component.id: component for component in components}


def _staff_read(appeal: FamilyRequest, component: ComponentType) -> FamilyRequestRead:
    return FamilyRequestRead(
        id=appeal.id,
        requester_name=appeal.requester_name,
        requester_phone=appeal.requester_phone,
        recipient_group=appeal.recipient_group,
        component_code=component.code,
        component_name=component.name,
        units_needed=appeal.units_needed,
        ward_reference=appeal.ward_reference,
        notes=appeal.notes,
        status=appeal.status,
        created_at=appeal.created_at,
        decided_at=appeal.decided_at,
        decline_reason=appeal.decline_reason,
        blood_request_id=appeal.blood_request_id,
    )


# ---------------------------------------------------------------------------------------
# Public: families
# ---------------------------------------------------------------------------------------


@public_router.get(
    "/hospitals",
    response_model=list[PublicHospitalRead],
    summary="Find verified hospitals",
)
def list_public_hospitals(
    session: SessionDep,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    postcode: Annotated[OptionalPostcode, Query(max_length=40)] = None,
) -> list[PublicHospitalRead]:
    """Verified hospitals, closest first, for a family looking for the patient's hospital.

    Give a NIPOST postcode (the hospital's, or the family's own) to rank by postcode, a
    position to rank by distance, or both. At most ten hospitals are returned.
    """
    results = find_hospitals(
        session,
        latitude=latitude,
        longitude=longitude,
        postcode=postcode,
        limit=MAX_HOSPITALS_LISTED,
    )
    return [
        PublicHospitalRead(
            id=result.hospital.id,
            name=result.hospital.name,
            address=result.hospital.address,
            city=result.hospital.city,
            state=result.hospital.state,
            postcode=result.hospital.postcode,
            contact_phone=result.hospital.contact_phone,
            latitude=result.hospital.latitude,
            longitude=result.hospital.longitude,
            distance_km=round(result.distance_km, 1) if result.distance_km is not None else None,
            postcode_ring=result.postcode_ring,
        )
        for result in results
    ]


@public_router.post(
    "/hospitals/{hospital_id}/family-requests",
    response_model=FamilyRequestCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Ask a verified hospital to find donors",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such verified hospital"},
        status.HTTP_409_CONFLICT: {"description": "This phone already has requests waiting"},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too many requests sent"},
    },
)
def send_family_request(
    hospital_id: UUID,
    payload: FamilyRequestCreate,
    session: SessionDep,
    ip_address: ClientIp,
) -> FamilyRequestCreated:
    """Send a family's appeal to a hospital. Nobody is alerted until the hospital confirms.

    Limited per network address and phone number, and each phone number may have only a
    couple of appeals waiting at once.
    """
    limiter = get_appeal_limiter()
    key = f"{ip_address}|{payload.requester_phone}"
    if limiter.is_blocked(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests have been sent. Call the hospital directly, or try later.",
        )
    limiter.record_failure(key)

    try:
        appeal, hospital = create_family_request(session, hospital_id, payload)
    except HospitalNotAvailableError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This hospital is not available on BloodLink.",
        ) from None
    except UnknownComponentError:
        raise HTTPException(
            status_code=422, detail="Unknown or unavailable blood component."
        ) from None
    except TooManyPendingError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This phone number already has requests waiting for a hospital to answer.",
        ) from None
    return FamilyRequestCreated(id=appeal.id, status=appeal.status, hospital_name=hospital.name)


@public_router.get(
    "/family-requests/{appeal_id}",
    response_model=FamilyRequestTracking,
    summary="Follow a family's request",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such request"}},
)
def track_family_request(appeal_id: UUID, session: SessionDep) -> FamilyRequestTracking:
    """Where an appeal stands. Its id is the family's private link; nothing personal is shown."""
    try:
        appeal = get_family_request(session, appeal_id)
    except FamilyRequestNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND) from None
    hospital = session.get(Hospital, appeal.hospital_id)
    component = session.get(ComponentType, appeal.component_type_id)
    assert hospital is not None and component is not None

    request_read: RequestRead | None = None
    if appeal.blood_request_id is not None:
        request = session.get(BloodRequest, appeal.blood_request_id)
        if request is not None:
            request_read = build_reads(session, [request])[0]

    return FamilyRequestTracking(
        id=appeal.id,
        status=appeal.status,
        hospital_name=hospital.name,
        hospital_postcode=hospital.postcode,
        hospital_phone=hospital.contact_phone,
        recipient_group=appeal.recipient_group,
        component_name=component.name,
        units_needed=request_read.units_needed if request_read else appeal.units_needed,
        created_at=appeal.created_at,
        decided_at=appeal.decided_at,
        decline_reason=appeal.decline_reason,
        request_status=request_read.status if request_read else None,
        units_pledged=request_read.units_pledged if request_read else None,
    )


# ---------------------------------------------------------------------------------------
# Hospital staff
# ---------------------------------------------------------------------------------------


@router.get("", response_model=list[FamilyRequestRead], summary="Requests from families")
def list_family_requests(
    hospital: VerifiedHospital,
    session: SessionDep,
    request_status: Annotated[
        FamilyRequestStatus | None, Query(alias="status", description="Only this state.")
    ] = None,
) -> list[FamilyRequestRead]:
    """Families' appeals to the staff member's hospital, waiting ones first."""
    appeals = list(list_for_hospital(session, hospital.id, status=request_status))
    components = _component_names(session, appeals)
    return [_staff_read(appeal, components[appeal.component_type_id]) for appeal in appeals]


@router.post(
    "/{appeal_id}/approve",
    response_model=FamilyRequestRead,
    summary="Confirm a family's request and alert donors",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such request for this hospital"},
        status.HTTP_409_CONFLICT: {"description": "Already decided, or too many open requests"},
    },
)
def approve(
    appeal_id: UUID,
    payload: FamilyRequestApprove,
    staff: StaffUser,
    hospital: VerifiedHospital,
    session: SessionDep,
    ip_address: ClientIp,
    background_tasks: BackgroundTasks,
) -> FamilyRequestRead:
    """Raise a blood request from the appeal, once staff have found the patient.

    Matched donors are texted exactly as for any new request, and the family is told.
    """
    try:
        appeal, request = approve_family_request(
            session, staff, hospital, appeal_id, payload, ip_address=ip_address
        )
    except FamilyRequestNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND) from None
    except AlreadyDecidedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This request was already decided."
        ) from None
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["body", *e["loc"]], "msg": e["msg"]} for e in exc.errors()],
        ) from None
    except UnknownComponentError:
        raise HTTPException(
            status_code=422, detail="Unknown or unavailable blood component."
        ) from None
    except TooManyOpenRequestsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your hospital has too many open requests. Close some before raising more.",
        ) from None

    engine = session.get_bind()
    background_tasks.add_task(alert_in_background, engine, request.id)
    background_tasks.add_task(_notify_family_in_background, engine, appeal.id)
    component = session.get(ComponentType, appeal.component_type_id)
    assert component is not None
    return _staff_read(appeal, component)


@router.post(
    "/{appeal_id}/decline",
    response_model=FamilyRequestRead,
    summary="Decline a family's request",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such request for this hospital"},
        status.HTTP_409_CONFLICT: {"description": "Already decided"},
    },
)
def decline(
    appeal_id: UUID,
    payload: FamilyRequestDecline,
    staff: StaffUser,
    hospital: VerifiedHospital,
    session: SessionDep,
    ip_address: ClientIp,
    background_tasks: BackgroundTasks,
) -> FamilyRequestRead:
    """Turn the appeal down with a reason, which the family sees and is texted."""
    try:
        appeal = decline_family_request(
            session, staff, hospital, appeal_id, reason=payload.reason, ip_address=ip_address
        )
    except FamilyRequestNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND) from None
    except AlreadyDecidedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This request was already decided."
        ) from None

    background_tasks.add_task(_notify_family_in_background, session.get_bind(), appeal.id)
    component = session.get(ComponentType, appeal.component_type_id)
    assert component is not None
    return _staff_read(appeal, component)
