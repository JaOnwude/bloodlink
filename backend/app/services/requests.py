"""Blood requests: creating, reading, closing and expiring them.

A request moves through these states:

    open -> fulfilled -> closed      (fulfilled happens when enough donors have pledged)
    open -> closed                   (the hospital withdraws it)
    open -> expired                  (the deadline passes first)

Expiry never depends on a scheduler running on time. Whenever requests are read, any that
are past their deadline are moved to ``expired`` first, so what the hospital sees is always
current. The ``scripts.expire_requests`` command does the same sweep for all hospitals, for
example from a periodic job.

Every change is written to the audit log in the same transaction.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import BloodRequest, ComponentType, Hospital, Pledge, User
from app.models.base import utcnow
from app.models.enums import PledgeStatus, RequestStatus
from app.schemas.request import RequestCreate, RequestRead
from app.services.audit import record_audit

# A hospital cannot have more than this many open requests at once. It stops accidental or
# abusive floods of alerts to donors.
MAX_OPEN_REQUESTS_PER_HOSPITAL = 25

# Pledge states that use up one of the units a request asks for.
COUNTED_PLEDGE_STATES = (PledgeStatus.PLEDGED, PledgeStatus.DONATED)


class RequestNotFoundError(Exception):
    """The request does not exist, or belongs to another hospital."""


class InvalidRequestStateError(Exception):
    """The action is not allowed in the request's current state."""


class UnknownComponentError(Exception):
    """The requested blood component does not exist or is not active."""


class TooManyOpenRequestsError(Exception):
    """The hospital already has the maximum number of open requests."""


def _snapshot(request: BloodRequest) -> dict[str, Any]:
    """JSON-friendly copy of the fields recorded in the audit log."""
    return {
        "recipient_group": request.recipient_group.value,
        "units_needed": request.units_needed,
        "urgency": request.urgency.value,
        "deadline": request.deadline.isoformat(),
        "status": request.status.value,
    }


def expire_overdue(
    session: Session, *, hospital_id: UUID | None = None, now: datetime | None = None
) -> int:
    """Move open requests whose deadline has passed to ``expired``.

    Args:
        hospital_id: Only this hospital's requests, or every hospital's when None.
        now: The moment to compare deadlines against; defaults to the current time.

    Returns:
        The number of requests that were expired.

    Rows another transaction is already changing are skipped rather than waited for; the
    next call picks them up if they are still overdue.
    """
    moment = now or utcnow()
    query = select(BloodRequest).where(
        BloodRequest.status == RequestStatus.OPEN,
        col(BloodRequest.deadline) <= moment,
    )
    if hospital_id is not None:
        query = query.where(BloodRequest.hospital_id == hospital_id)

    overdue = session.exec(query.with_for_update(skip_locked=True)).all()
    for request in overdue:
        before = _snapshot(request)
        request.status = RequestStatus.EXPIRED
        session.add(request)
        record_audit(
            session,
            actor=None,
            action="request.expired",
            entity_type="blood_request",
            entity_id=request.id,
            before=before,
            after=_snapshot(request),
        )
    if overdue:
        session.commit()
    return len(overdue)


def create_request(
    session: Session,
    staff: User,
    hospital: Hospital,
    data: RequestCreate,
    *,
    ip_address: str | None,
) -> BloodRequest:
    """Raise a new request on behalf of a verified hospital.

    Raises:
        UnknownComponentError: If the component code is not a known, active component.
        TooManyOpenRequestsError: If the hospital is at its limit of open requests.
    """
    component = session.exec(
        select(ComponentType).where(
            ComponentType.code == data.component_code,
            col(ComponentType.is_active).is_(True),
        )
    ).first()
    if component is None:
        raise UnknownComponentError(data.component_code)

    # Settle overdue requests first so they do not count against the limit.
    expire_overdue(session, hospital_id=hospital.id)
    open_count = session.exec(
        select(func.count())
        .select_from(BloodRequest)
        .where(
            BloodRequest.hospital_id == hospital.id,
            BloodRequest.status == RequestStatus.OPEN,
        )
    ).one()
    if open_count >= MAX_OPEN_REQUESTS_PER_HOSPITAL:
        raise TooManyOpenRequestsError(str(hospital.id))

    request = BloodRequest(
        hospital_id=hospital.id,
        created_by=staff.id,
        recipient_group=data.recipient_group,
        component_type_id=component.id,
        units_needed=data.units_needed,
        urgency=data.urgency,
        deadline=data.deadline,
        notes=data.notes,
    )
    session.add(request)
    record_audit(
        session,
        actor=staff,
        action="request.created",
        entity_type="blood_request",
        entity_id=request.id,
        after=_snapshot(request),
        ip_address=ip_address,
    )
    session.commit()
    session.refresh(request)
    return request


def get_request(session: Session, request_id: UUID, hospital_id: UUID | None) -> BloodRequest:
    """Return one of the hospital's own requests, with expiry applied.

    A request that belongs to another hospital is reported as not found, so the existence
    of other hospitals' requests is never revealed.

    Raises:
        RequestNotFoundError: If it does not exist or is not this hospital's.
    """
    request = session.get(BloodRequest, request_id)
    if request is None or hospital_id is None or request.hospital_id != hospital_id:
        raise RequestNotFoundError(str(request_id))

    if request.status == RequestStatus.OPEN and request.deadline <= utcnow():
        expire_overdue(session, hospital_id=hospital_id)
        session.refresh(request)
    return request


def list_requests(
    session: Session,
    hospital_id: UUID | None,
    *,
    status: RequestStatus | None,
    limit: int,
    offset: int,
) -> tuple[Sequence[BloodRequest], int]:
    """One page of a hospital's requests, newest first, and the total that match."""
    if hospital_id is None:
        return [], 0

    expire_overdue(session, hospital_id=hospital_id)

    filters = [BloodRequest.hospital_id == hospital_id]
    if status is not None:
        filters.append(BloodRequest.status == status)

    total = session.exec(select(func.count()).select_from(BloodRequest).where(*filters)).one()
    items = session.exec(
        select(BloodRequest)
        .where(*filters)
        .order_by(col(BloodRequest.created_at).desc(), col(BloodRequest.id))
        .limit(limit)
        .offset(offset)
    ).all()
    return items, total


def close_request(
    session: Session,
    staff: User,
    request_id: UUID,
    hospital_id: UUID | None,
    *,
    ip_address: str | None,
) -> BloodRequest:
    """Close a request, for example because the need has passed.

    Raises:
        RequestNotFoundError: If it does not exist or is not this hospital's.
        InvalidRequestStateError: If it is already closed or has expired.
    """
    request = get_request(session, request_id, hospital_id)

    # Lock the row so a pledge arriving at the same moment cannot interleave with the change.
    locked = session.get(BloodRequest, request.id, with_for_update=True)
    if locked is None:
        raise RequestNotFoundError(str(request_id))
    if locked.status not in (RequestStatus.OPEN, RequestStatus.FULFILLED):
        raise InvalidRequestStateError(f"This request is already {locked.status.value}.")

    before = _snapshot(locked)
    locked.status = RequestStatus.CLOSED
    session.add(locked)
    record_audit(
        session,
        actor=staff,
        action="request.closed",
        entity_type="blood_request",
        entity_id=locked.id,
        before=before,
        after=_snapshot(locked),
        ip_address=ip_address,
    )
    session.commit()
    session.refresh(locked)
    return locked


def build_reads(session: Session, requests: Sequence[BloodRequest]) -> list[RequestRead]:
    """Turn requests into their API form, adding component names and pledge counts.

    Names and counts are fetched for the whole list in two queries, not one per request.
    """
    if not requests:
        return []

    component_ids = {request.component_type_id for request in requests}
    components = {
        component.id: component
        for component in session.exec(
            select(ComponentType).where(col(ComponentType.id).in_(component_ids))
        ).all()
    }
    pledged = dict(
        session.exec(
            select(Pledge.request_id, func.count())
            .where(
                col(Pledge.request_id).in_([request.id for request in requests]),
                col(Pledge.status).in_(COUNTED_PLEDGE_STATES),
            )
            .group_by(Pledge.request_id)
        ).all()
    )

    reads: list[RequestRead] = []
    for request in requests:
        component = components[request.component_type_id]
        units_pledged = pledged.get(request.id, 0)
        reads.append(
            RequestRead(
                id=request.id,
                hospital_id=request.hospital_id,
                recipient_group=request.recipient_group,
                component_code=component.code,
                component_name=component.name,
                units_needed=request.units_needed,
                units_pledged=units_pledged,
                units_remaining=max(request.units_needed - units_pledged, 0),
                urgency=request.urgency,
                deadline=request.deadline,
                notes=request.notes,
                status=request.status,
                fulfilled_at=request.fulfilled_at,
                created_at=request.created_at,
            )
        )
    return reads
