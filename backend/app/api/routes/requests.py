"""Blood request endpoints for hospital staff, including the text-message alerts to donors.

Raising a request needs a verified hospital. Reading, closing and matching are scoped to the
signed-in staff member's own hospital: a request that belongs to another hospital is
reported as not found.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlmodel import Session

from app.api.deps import ClientIp, SessionDep, StaffUser, VerifiedHospital
from app.core.config import get_settings
from app.models import Hospital
from app.models.enums import RequestStatus
from app.schemas.notification import AlertRunRead, AlertSummary
from app.schemas.request import (
    MAX_SEARCH_RADIUS_KM,
    MatchesResponse,
    MatchRead,
    RequestCreate,
    RequestPage,
    RequestRead,
)
from app.services.distance import approximate_position
from app.services.matching import Match, find_matches
from app.services.notifications import alert_in_background, alert_matched_donors, count_alerts
from app.services.requests import (
    InvalidRequestStateError,
    RequestNotFoundError,
    TooManyOpenRequestsError,
    UnknownComponentError,
    build_reads,
    close_request,
    create_request,
    get_request,
    list_requests,
)
from app.services.sms import active_provider

router = APIRouter(prefix="/requests", tags=["requests"])

_NOT_FOUND = "Request not found."


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)


@router.post(
    "",
    response_model=RequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="Raise a blood request",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Hospital is not verified"},
        status.HTTP_409_CONFLICT: {"description": "Too many open requests"},
    },
)
def raise_request(
    payload: RequestCreate,
    staff: StaffUser,
    hospital: VerifiedHospital,
    session: SessionDep,
    ip_address: ClientIp,
    background_tasks: BackgroundTasks,
) -> RequestRead:
    """Ask for blood on behalf of the staff member's verified hospital.

    Matched donors are sent a text message once the response has gone out, so the hospital
    is not kept waiting for the SMS provider. Alerting never makes this call fail.
    """
    try:
        request = create_request(session, staff, hospital, payload, ip_address=ip_address)
    except UnknownComponentError:
        raise HTTPException(
            status_code=422,  # Unprocessable: the constant's name differs between versions.
            detail="Unknown or unavailable blood component.",
        ) from None
    except TooManyOpenRequestsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your hospital has too many open requests. Close some before raising more.",
        ) from None
    background_tasks.add_task(alert_in_background, session.get_bind(), request.id)
    return build_reads(session, [request])[0]


@router.get("", response_model=RequestPage, summary="My hospital's requests")
def list_my_requests(
    staff: StaffUser,
    session: SessionDep,
    request_status: Annotated[
        RequestStatus | None,
        Query(alias="status", description="Only requests in this state."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RequestPage:
    """List the hospital's requests, newest first."""
    requests, total = list_requests(
        session, staff.hospital_id, status=request_status, limit=limit, offset=offset
    )
    return RequestPage(
        items=build_reads(session, requests), total=total, limit=limit, offset=offset
    )


@router.get(
    "/{request_id}",
    response_model=RequestRead,
    summary="One request",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such request"}},
)
def read_request(request_id: UUID, staff: StaffUser, session: SessionDep) -> RequestRead:
    """Return one of the hospital's requests."""
    try:
        request = get_request(session, request_id, staff.hospital_id)
    except RequestNotFoundError:
        raise _not_found() from None
    return build_reads(session, [request])[0]


@router.post(
    "/{request_id}/close",
    response_model=RequestRead,
    summary="Close a request",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such request"},
        status.HTTP_409_CONFLICT: {"description": "Already closed or expired"},
    },
)
def close_my_request(
    request_id: UUID, staff: StaffUser, session: SessionDep, ip_address: ClientIp
) -> RequestRead:
    """Withdraw a request that is no longer needed."""
    try:
        request = close_request(
            session, staff, request_id, staff.hospital_id, ip_address=ip_address
        )
    except RequestNotFoundError:
        raise _not_found() from None
    except InvalidRequestStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return build_reads(session, [request])[0]


def _match_read(match: Match) -> MatchRead:
    latitude, longitude = approximate_position(match.donor.latitude, match.donor.longitude)
    return MatchRead(
        donor_id=match.donor.id,
        blood_group=match.donor.blood_group,
        city=match.donor.city,
        distance_km=round(match.distance_km, 1),
        approx_latitude=latitude,
        approx_longitude=longitude,
    )


@router.get(
    "/{request_id}/matches",
    response_model=MatchesResponse,
    summary="Donors who can answer a request",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such request"},
        status.HTTP_409_CONFLICT: {"description": "Request is not open"},
    },
)
def read_matches(
    request_id: UUID,
    staff: StaffUser,
    session: SessionDep,
    radius_km: Annotated[float | None, Query(gt=0, le=MAX_SEARCH_RADIUS_KM)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> MatchesResponse:
    """Compatible, eligible, available donors near the hospital, nearest first.

    The list is anonymous: it shows blood group, city, distance and a position rounded to
    about a kilometre for the map. Contact details are revealed to the hospital only after a
    donor pledges.
    """
    try:
        request = get_request(session, request_id, staff.hospital_id)
    except RequestNotFoundError:
        raise _not_found() from None

    if request.status != RequestStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Matches are only available for open requests.",
        )

    # The hospital exists: the request belongs to it.
    hospital = session.get(Hospital, request.hospital_id)
    if hospital is None:
        raise _not_found()

    radius = radius_km if radius_km is not None else get_settings().default_search_radius_km
    matches, total = find_matches(session, request, hospital, radius_km=radius, limit=limit)
    return MatchesResponse(
        items=[_match_read(match) for match in matches],
        total=total,
        radius_km=radius,
    )


def _alert_summary(session: Session, request_id: UUID) -> AlertSummary:
    counts = count_alerts(session, request_id)
    return AlertSummary(
        sent=counts.sent,
        failed=counts.failed,
        queued=counts.queued,
        total=counts.total,
        provider=active_provider(),
    )


@router.get(
    "/{request_id}/alerts",
    response_model=AlertSummary,
    summary="Alerts sent about a request",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such request"}},
)
def read_alerts(request_id: UUID, staff: StaffUser, session: SessionDep) -> AlertSummary:
    """How many donors have been texted about the request, by delivery state."""
    try:
        get_request(session, request_id, staff.hospital_id)
    except RequestNotFoundError:
        raise _not_found() from None
    return _alert_summary(session, request_id)


@router.post(
    "/{request_id}/alerts",
    response_model=AlertRunRead,
    summary="Alert matched donors",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such request"},
        status.HTTP_409_CONFLICT: {"description": "Request is not open"},
    },
)
def send_alerts(
    request_id: UUID,
    staff: StaffUser,
    hospital: VerifiedHospital,
    session: SessionDep,
    radius_km: Annotated[float | None, Query(gt=0, le=MAX_SEARCH_RADIUS_KM)] = None,
) -> AlertRunRead:
    """Text matched donors who have not been alerted about this request yet.

    Useful after widening the search radius: only the donors the wider search adds are
    messaged. Donors already alerted are never messaged again.
    """
    try:
        request = get_request(session, request_id, hospital.id)
    except RequestNotFoundError:
        raise _not_found() from None
    if request.status != RequestStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Alerts can only be sent for open requests.",
        )

    run = alert_matched_donors(session, request.id, radius_km=radius_km)
    return AlertRunRead(
        matched=run.matched,
        newly_alerted=run.newly_alerted,
        sent=run.sent,
        failed=run.failed,
        already_alerted=run.already_alerted,
        without_phone=run.without_phone,
        totals=_alert_summary(session, request.id),
    )
