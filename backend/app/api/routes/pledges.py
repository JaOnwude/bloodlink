"""Pledge endpoints: donors committing to requests, and staff recording the outcome.

Donors pledge, join a standby reserve, or cancel. Hospital staff list the pledges for their
own requests and record what happened: donated, did not attend, or deferred at screening.
Pledges for another hospital's request, or another donor's pledge, are reported as not
found, so their existence is never revealed.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlmodel import Session

from app.api.deps import ClientIp, DonorUser, SessionDep, StaffUser
from app.data.deferral_rules import DEFERRAL_RULES
from app.models import Donor
from app.models.enums import DeferralReason, PledgeStatus
from app.schemas.pledge import (
    DeferralCreate,
    DeferralReasonRead,
    HospitalPledgeRead,
    PledgedDonor,
    PledgeRead,
)
from app.services.donors import get_donor_for_user
from app.services.notifications import notify_promoted_in_background
from app.services.pledges import (
    ActivePledgeError,
    AlreadyPledgedError,
    InvalidPledgeStateError,
    NotEligibleError,
    PledgeNotFoundError,
    PledgeOutcome,
    RequestFullError,
    RequestNotOpenError,
    cancel_pledge,
    count_standby,
    count_taken_units,
    create_pledge,
    list_request_pledges,
    resolve_pledge,
)
from app.services.requests import RequestNotFoundError

router = APIRouter(tags=["pledges"])

_REQUEST_NOT_FOUND = "Request not found."
_PLEDGE_NOT_FOUND = "Pledge not found."

# Once a donor withdraws or is released from standby, their contact details are no longer
# shared with the hospital.
_CONTACT_WITHHELD = (PledgeStatus.CANCELLED, PledgeStatus.RELEASED)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _require_donor_profile(session: Session, user: DonorUser) -> Donor:
    donor = get_donor_for_user(session, user)
    if donor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create your donor profile before pledging.",
        )
    return donor


def _pledge_read(session: Session, outcome: PledgeOutcome) -> PledgeRead:
    taken = count_taken_units(session, outcome.request.id)
    waiting = count_standby(session, outcome.request.id)
    return PledgeRead(
        id=outcome.pledge.id,
        request_id=outcome.request.id,
        status=outcome.pledge.status,
        pledged_at=outcome.pledge.pledged_at,
        resolved_at=outcome.pledge.resolved_at,
        request_status=outcome.request.status,
        units_remaining=max(outcome.request.units_needed - taken, 0),
        standby_places_left=max(outcome.request.standby_units - waiting, 0),
    )


def _tell_promoted(
    background_tasks: BackgroundTasks, session: Session, outcome: PledgeOutcome
) -> None:
    """Text the standby donor who was moved up, once the response has gone out."""
    if outcome.promoted is not None:
        background_tasks.add_task(
            notify_promoted_in_background, session.get_bind(), outcome.promoted.id
        )


@router.post(
    "/requests/{request_id}/pledges",
    response_model=PledgeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Pledge to a request",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Incompatible or not eligible today"},
        status.HTTP_404_NOT_FOUND: {"description": "No such request, or no donor profile"},
        status.HTTP_409_CONFLICT: {
            "description": "Request not open, already full, or the donor already pledged"
        },
    },
)
def pledge_to_request(
    request_id: UUID, user: DonorUser, session: SessionDep, ip_address: ClientIp
) -> PledgeRead:
    """Commit the signed-in donor to a request, or join its standby reserve.

    Safe under concurrency: when several donors pledge for the last unit at the same
    instant, exactly one succeeds. The pledge that takes the last unit moves the request to
    ``fulfilled``. After that, donors join the standby reserve (status ``standby``) while
    places are left, and anyone after them receives 409.
    """
    donor = _require_donor_profile(session, user)
    try:
        outcome = create_pledge(session, user, donor, request_id, ip_address=ip_address)
    except RequestNotFoundError:
        raise _not_found(_REQUEST_NOT_FOUND) from None
    except NotEligibleError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from None
    except (RequestNotOpenError, RequestFullError, AlreadyPledgedError, ActivePledgeError) as exc:
        raise _conflict(exc) from None
    return _pledge_read(session, outcome)


@router.get(
    "/requests/{request_id}/pledges",
    response_model=list[HospitalPledgeRead],
    summary="Pledges for one of my hospital's requests",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such request"}},
)
def read_request_pledges(
    request_id: UUID, staff: StaffUser, session: SessionDep
) -> list[HospitalPledgeRead]:
    """List who has pledged to the request, oldest first, with their contact details.

    Contact details are shown because the donor shared them by pledging, including donors
    on standby, who may be called. They are left out once a donor cancels or is released
    from standby.
    """
    try:
        views = list_request_pledges(session, request_id, staff.hospital_id)
    except RequestNotFoundError:
        raise _not_found(_REQUEST_NOT_FOUND) from None

    items: list[HospitalPledgeRead] = []
    for view in views:
        share = view.pledge.status not in _CONTACT_WITHHELD
        items.append(
            HospitalPledgeRead(
                id=view.pledge.id,
                status=view.pledge.status,
                pledged_at=view.pledge.pledged_at,
                resolved_at=view.pledge.resolved_at,
                deferral_reason=view.pledge.deferral_reason,
                donor=PledgedDonor(
                    donor_id=view.donor.id,
                    blood_group=view.donor.blood_group,
                    city=view.donor.city,
                    full_name=view.user.full_name if share else None,
                    phone=view.user.phone if share else None,
                    email=view.user.email if share else None,
                ),
            )
        )
    return items


@router.delete(
    "/pledges/{pledge_id}",
    response_model=PledgeRead,
    summary="Cancel my pledge",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such pledge"},
        status.HTTP_409_CONFLICT: {"description": "Pledge already resolved or cancelled"},
    },
)
def cancel_my_pledge(
    pledge_id: UUID,
    user: DonorUser,
    session: SessionDep,
    ip_address: ClientIp,
    background_tasks: BackgroundTasks,
) -> PledgeRead:
    """Withdraw one of the signed-in donor's pledges, or step down from standby.

    A cancelled pledge frees its unit: the longest-waiting standby donor is called in and
    texted, or, with nobody on standby, a fulfilled request whose deadline is ahead reopens.
    """
    donor = _require_donor_profile(session, user)
    try:
        outcome = cancel_pledge(session, user, donor, pledge_id, ip_address=ip_address)
    except PledgeNotFoundError:
        raise _not_found(_PLEDGE_NOT_FOUND) from None
    except InvalidPledgeStateError as exc:
        raise _conflict(exc) from None
    _tell_promoted(background_tasks, session, outcome)
    return _pledge_read(session, outcome)


def _resolve(
    pledge_id: UUID,
    staff: StaffUser,
    session: Session,
    ip_address: str | None,
    background_tasks: BackgroundTasks,
    *,
    outcome: PledgeStatus,
    reason: DeferralReason | None = None,
) -> PledgeRead:
    try:
        result = resolve_pledge(
            session,
            staff,
            pledge_id,
            outcome=outcome,
            deferral_reason=reason,
            ip_address=ip_address,
        )
    except PledgeNotFoundError:
        raise _not_found(_PLEDGE_NOT_FOUND) from None
    except InvalidPledgeStateError as exc:
        raise _conflict(exc) from None
    _tell_promoted(background_tasks, session, result)
    return _pledge_read(session, result)


@router.post(
    "/pledges/{pledge_id}/donated",
    response_model=PledgeRead,
    summary="Confirm a donation",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such pledge"},
        status.HTTP_409_CONFLICT: {"description": "Pledge already resolved or cancelled"},
    },
)
def confirm_donation(
    pledge_id: UUID,
    staff: StaffUser,
    session: SessionDep,
    ip_address: ClientIp,
    background_tasks: BackgroundTasks,
) -> PledgeRead:
    """Record that the donor gave blood.

    Creates the donation record and updates the donor's last donation date in the same
    transaction, so their waiting period starts immediately. Once every unit the request
    needs has been given, any standby donors are released.
    """
    return _resolve(
        pledge_id, staff, session, ip_address, background_tasks, outcome=PledgeStatus.DONATED
    )


@router.post(
    "/pledges/{pledge_id}/no-show",
    response_model=PledgeRead,
    summary="Record a no-show",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such pledge"},
        status.HTTP_409_CONFLICT: {"description": "Pledge already resolved or cancelled"},
    },
)
def record_no_show(
    pledge_id: UUID,
    staff: StaffUser,
    session: SessionDep,
    ip_address: ClientIp,
    background_tasks: BackgroundTasks,
) -> PledgeRead:
    """Record that the donor did not come. The unit goes to the next standby donor."""
    return _resolve(
        pledge_id, staff, session, ip_address, background_tasks, outcome=PledgeStatus.NO_SHOW
    )


@router.post(
    "/pledges/{pledge_id}/deferred",
    response_model=PledgeRead,
    summary="Record a deferral at screening",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such pledge"},
        status.HTTP_409_CONFLICT: {
            "description": "Pledge already resolved, cancelled or on standby"
        },
    },
)
def record_deferral(
    pledge_id: UUID,
    payload: DeferralCreate,
    staff: StaffUser,
    session: SessionDep,
    ip_address: ClientIp,
    background_tasks: BackgroundTasks,
) -> PledgeRead:
    """Record that the donor came but was turned away at screening.

    The donor is deferred for the period set for the reason, permanently for a positive
    infection screen. Only the reason category is stored, never a result. The unit goes to
    the next standby donor, who is texted.
    """
    return _resolve(
        pledge_id,
        staff,
        session,
        ip_address,
        background_tasks,
        outcome=PledgeStatus.DEFERRED,
        reason=payload.reason,
    )


@router.get(
    "/deferral-reasons",
    response_model=list[DeferralReasonRead],
    summary="Reasons a donor can be deferred at screening",
)
def list_deferral_reasons(staff: StaffUser) -> list[DeferralReasonRead]:
    """The screening outcomes staff can record, with how long each defers the donor.

    Read from ``app.data.deferral_rules``, so the form always matches the rules in force.
    """
    return [
        DeferralReasonRead(code=reason, label=rule.staff_label, deferral_days=rule.days)
        for reason, rule in DEFERRAL_RULES.items()
    ]
