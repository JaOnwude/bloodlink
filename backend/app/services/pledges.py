"""Pledges: donors committing to a request, and hospitals recording what happened.

A pledge moves through these states:

    pledged -> donated      (staff confirm the donation took place)
    pledged -> no_show      (staff record that the donor did not come)
    pledged -> cancelled    (the donor withdraws; they may pledge again later)

The central guarantee is that a request is never promised more units than it needs, even
when several donors accept at the same instant. Every operation that changes how many
units are taken runs in one transaction that first locks the request row with
``SELECT ... FOR UPDATE``. A second transaction touching the same request waits at that
lock until the first commits, and then counts the pledges again, so the count it compares
against ``units_needed`` is always the committed truth.

A donor may hold only one active pledge at a time, because they can only give once per
waiting period. That rule is protected the same way, by locking the donor's row first.
Locks are always taken in the same order (donor, then request), so two transactions can
never each hold the lock the other is waiting for.

Every change is written to the audit log in the same transaction.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.models import (
    BloodCompatibility,
    BloodRequest,
    ComponentType,
    Donation,
    Donor,
    DonorDeferral,
    Hospital,
    Pledge,
    User,
)
from app.models.base import utcnow
from app.models.enums import PledgeStatus, RequestStatus
from app.services.audit import record_audit
from app.services.eligibility import evaluate_eligibility
from app.services.requests import COUNTED_PLEDGE_STATES, RequestNotFoundError, expire_overdue


class PledgeNotFoundError(Exception):
    """The pledge does not exist, or belongs to someone else."""


class RequestNotOpenError(Exception):
    """The request is fulfilled, closed or expired, so it cannot take pledges."""


class RequestFullError(Exception):
    """Every unit the request needs has already been pledged."""


class AlreadyPledgedError(Exception):
    """The donor already has a pledge for this request."""


class ActivePledgeError(Exception):
    """The donor already has an unresolved pledge for another request."""


class NotEligibleError(Exception):
    """The donor cannot answer this request: incompatible group or not eligible today."""


class InvalidPledgeStateError(Exception):
    """The action is not allowed in the pledge's current state."""


@dataclass(frozen=True)
class PledgeOutcome:
    """A pledge together with the request it belongs to, after a change."""

    pledge: Pledge
    request: BloodRequest


def _pledge_snapshot(pledge: Pledge) -> dict[str, Any]:
    """JSON-friendly copy of the pledge fields recorded in the audit log."""
    return {
        "request_id": str(pledge.request_id),
        "donor_id": str(pledge.donor_id),
        "status": pledge.status.value,
    }


def _request_snapshot(request: BloodRequest) -> dict[str, Any]:
    """JSON-friendly copy of the request fields recorded in the audit log."""
    return {"status": request.status.value, "units_needed": request.units_needed}


def _lock_request(session: Session, request_id: UUID) -> BloodRequest | None:
    """Load a request and hold its row lock until the transaction ends.

    ``populate_existing`` makes sure the values come from the locked read, not from an
    older copy the session may already hold.
    """
    return session.exec(
        select(BloodRequest)
        .where(BloodRequest.id == request_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()


def _lock_donor(session: Session, donor_id: UUID) -> Donor | None:
    """Load the donor and hold their row lock until the transaction ends.

    The fresh copy matters: eligibility depends on the last donation date, which a
    hospital may have just updated.
    """
    return session.exec(
        select(Donor)
        .where(Donor.id == donor_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()


def count_taken_units(session: Session, request_id: UUID) -> int:
    """Number of the request's units taken by pledges that are active or already donated."""
    return session.exec(
        select(func.count())
        .select_from(Pledge)
        .where(
            Pledge.request_id == request_id,
            col(Pledge.status).in_(COUNTED_PLEDGE_STATES),
        )
    ).one()


def _reopen_if_short(session: Session, request: BloodRequest, *, actor: User | None) -> None:
    """Move a fulfilled request back to open when a unit has been freed.

    Only a request whose deadline is still ahead is reopened; one whose deadline has passed
    stays as it is, since nobody could pledge to it in time. Must be called with the
    request row locked, after the freeing change has been added to the session.
    """
    if request.status != RequestStatus.FULFILLED or request.deadline <= utcnow():
        return
    session.flush()
    if count_taken_units(session, request.id) >= request.units_needed:
        return

    before = _request_snapshot(request)
    request.status = RequestStatus.OPEN
    request.fulfilled_at = None
    session.add(request)
    record_audit(
        session,
        actor=actor,
        action="request.reopened",
        entity_type="blood_request",
        entity_id=request.id,
        before=before,
        after=_request_snapshot(request),
    )


def _check_donor_can_answer(
    session: Session, donor: Donor, request: BloodRequest, *, today: date
) -> None:
    """Confirm the donor's group is compatible and they may give this component today.

    The same rules as matching: compatibility comes from the ``blood_compatibility`` table
    and eligibility from the rules module.

    Raises:
        NotEligibleError: With a message the donor can act on.
    """
    compatible = session.exec(
        select(BloodCompatibility.id).where(
            BloodCompatibility.recipient_group == request.recipient_group,
            BloodCompatibility.donor_group == donor.blood_group,
        )
    ).first()
    if compatible is None:
        raise NotEligibleError(
            f"Your blood group ({donor.blood_group.value}) cannot be given to a patient "
            f"with {request.recipient_group.value}."
        )

    component = session.get(ComponentType, request.component_type_id)
    if component is None:
        raise NotEligibleError("This request asks for a component that is no longer offered.")
    deferrals = session.exec(select(DonorDeferral).where(DonorDeferral.donor_id == donor.id)).all()
    settings = get_settings()
    result = evaluate_eligibility(
        donor,
        [component],
        deferrals,
        today=today,
        min_age_years=settings.min_donor_age_years,
        max_age_years=settings.max_donor_age_years,
        min_weight_kg=settings.min_donor_weight_kg,
    )
    position = result.components[0]
    if not position.eligible:
        if result.blockers:
            raise NotEligibleError(result.blockers[0])
        when = f" until {position.next_eligible_date}" if position.next_eligible_date else ""
        raise NotEligibleError(f"You cannot give {component.name.lower()} again{when}.")


def create_pledge(
    session: Session,
    user: User,
    donor: Donor,
    request_id: UUID,
    *,
    ip_address: str | None,
    today: date | None = None,
) -> PledgeOutcome:
    """Commit a donor to a request, without ever exceeding the units it needs.

    Runs as one transaction:

    1. lock the donor's row, so the same donor cannot pledge to two requests at once;
    2. lock the request row, so competing pledges for it take turns;
    3. check the request is open and not past its deadline, and that the donor may answer
       it (compatible group, eligible today, no other active pledge, not already pledged);
    4. count the units already taken; refuse if none are left;
    5. record the pledge, and mark the request fulfilled if it took the last unit.

    A donor who cancelled earlier pledges again on the same row, which the unique
    constraint on (request, donor) requires.

    Raises:
        RequestNotFoundError: If there is no such request.
        RequestNotOpenError: If the request is not open, or its deadline has just passed.
        NotEligibleError: If the donor's group is incompatible or they may not give today.
        AlreadyPledgedError: If the donor already pledged to this request.
        ActivePledgeError: If the donor has an unresolved pledge for another request.
        RequestFullError: If every unit is already taken, including when the request
            has just been fulfilled by a competing pledge.
    """
    on_day = today or datetime.now(UTC).date()

    locked_donor = _lock_donor(session, donor.id)
    if locked_donor is None:
        session.rollback()
        raise NotEligibleError("Create your donor profile before pledging.")
    donor = locked_donor
    request = _lock_request(session, request_id)
    if request is None:
        session.rollback()
        raise RequestNotFoundError(str(request_id))

    if request.status == RequestStatus.OPEN and request.deadline <= utcnow():
        # Release the lock, then let the shared sweep record the expiry.
        session.rollback()
        expire_overdue(session, hospital_id=request.hospital_id)
        raise RequestNotOpenError("This request has expired.")
    if request.status == RequestStatus.FULFILLED:
        # Usually the outcome of losing a race for the last unit, so say exactly that.
        session.rollback()
        raise RequestFullError("Every unit this request needs has already been pledged.")
    if request.status != RequestStatus.OPEN:
        status = request.status.value
        session.rollback()
        raise RequestNotOpenError(f"This request is {status} and no longer takes pledges.")

    try:
        _check_donor_can_answer(session, donor, request, today=on_day)

        existing = session.exec(
            select(Pledge).where(Pledge.request_id == request.id, Pledge.donor_id == donor.id)
        ).first()
        if existing is not None and existing.status != PledgeStatus.CANCELLED:
            raise AlreadyPledgedError("You have already pledged to this request.")

        elsewhere = session.exec(
            select(Pledge.id).where(
                Pledge.donor_id == donor.id,
                Pledge.status == PledgeStatus.PLEDGED,
                Pledge.request_id != request.id,
            )
        ).first()
        if elsewhere is not None:
            raise ActivePledgeError(
                "You already have a pledge waiting for another request. Cancel it, or wait "
                "until the hospital records your donation, before pledging again."
            )

        if count_taken_units(session, request.id) >= request.units_needed:
            raise RequestFullError("Every unit this request needs has already been pledged.")
    except Exception:
        session.rollback()
        raise

    if existing is not None:
        pledge = existing
        before = _pledge_snapshot(pledge)
        pledge.status = PledgeStatus.PLEDGED
        pledge.pledged_at = utcnow()
        pledge.resolved_at = None
        pledge.resolved_by = None
    else:
        pledge = Pledge(request_id=request.id, donor_id=donor.id)
        before = None
    session.add(pledge)
    session.flush()
    record_audit(
        session,
        actor=user,
        action="pledge.created",
        entity_type="pledge",
        entity_id=pledge.id,
        before=before,
        after=_pledge_snapshot(pledge),
        ip_address=ip_address,
    )

    if count_taken_units(session, request.id) >= request.units_needed:
        request_before = _request_snapshot(request)
        request.status = RequestStatus.FULFILLED
        request.fulfilled_at = utcnow()
        session.add(request)
        record_audit(
            session,
            actor=None,
            action="request.fulfilled",
            entity_type="blood_request",
            entity_id=request.id,
            before=request_before,
            after=_request_snapshot(request),
        )

    session.commit()
    session.refresh(pledge)
    session.refresh(request)
    return PledgeOutcome(pledge=pledge, request=request)


def _lock_pledge_with_request(
    session: Session, pledge_id: UUID
) -> tuple[Pledge, BloodRequest] | None:
    """Lock a pledge's request and then the pledge itself, and return both.

    The request is locked first, matching the order used when pledging, so a cancellation
    or resolution can never deadlock with a new pledge for the same request.
    """
    request_id = session.exec(select(Pledge.request_id).where(Pledge.id == pledge_id)).first()
    if request_id is None:
        return None
    request = _lock_request(session, request_id)
    pledge = session.exec(
        select(Pledge)
        .where(Pledge.id == pledge_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).first()
    if request is None or pledge is None:
        return None
    return pledge, request


def cancel_pledge(
    session: Session, user: User, donor: Donor, pledge_id: UUID, *, ip_address: str | None
) -> PledgeOutcome:
    """Withdraw one of the donor's own pledges.

    The unit is freed. If the request had been fulfilled and its deadline is still ahead,
    it reopens so another donor can take the unit.

    Raises:
        PledgeNotFoundError: If there is no such pledge, or it belongs to another donor.
        InvalidPledgeStateError: If the pledge is not active (already resolved or cancelled).
    """
    locked = _lock_pledge_with_request(session, pledge_id)
    if locked is None or locked[0].donor_id != donor.id:
        session.rollback()
        raise PledgeNotFoundError(str(pledge_id))
    pledge, request = locked

    if pledge.status != PledgeStatus.PLEDGED:
        status = pledge.status.value.replace("_", " ")
        session.rollback()
        raise InvalidPledgeStateError(f"This pledge is already {status}.")

    before = _pledge_snapshot(pledge)
    pledge.status = PledgeStatus.CANCELLED
    session.add(pledge)
    record_audit(
        session,
        actor=user,
        action="pledge.cancelled",
        entity_type="pledge",
        entity_id=pledge.id,
        before=before,
        after=_pledge_snapshot(pledge),
        ip_address=ip_address,
    )
    _reopen_if_short(session, request, actor=None)

    session.commit()
    session.refresh(pledge)
    session.refresh(request)
    return PledgeOutcome(pledge=pledge, request=request)


def resolve_pledge(
    session: Session,
    staff: User,
    pledge_id: UUID,
    *,
    donated: bool,
    ip_address: str | None,
) -> PledgeOutcome:
    """Record whether a donor who pledged actually gave blood.

    When they donated, a ``donations`` row is created and the donor's cached
    ``last_donation_date`` is moved forward, all in this transaction, so the waiting
    period starts at once and matching stops offering the donor. When they did not come,
    the unit is freed and a fulfilled request whose deadline is still ahead reopens.

    An outcome can be recorded whatever state the request is now in: a donor may arrive
    just before a request is closed, and the record of what happened should still be kept.

    Raises:
        PledgeNotFoundError: If there is no such pledge, or it is for another hospital.
        InvalidPledgeStateError: If the pledge is not active (already resolved or cancelled).
    """
    locked = _lock_pledge_with_request(session, pledge_id)
    if locked is None or staff.hospital_id is None or locked[1].hospital_id != staff.hospital_id:
        session.rollback()
        raise PledgeNotFoundError(str(pledge_id))
    pledge, request = locked

    if pledge.status != PledgeStatus.PLEDGED:
        status = pledge.status.value.replace("_", " ")
        session.rollback()
        raise InvalidPledgeStateError(f"This pledge is already {status}.")

    now = utcnow()
    before = _pledge_snapshot(pledge)
    pledge.status = PledgeStatus.DONATED if donated else PledgeStatus.NO_SHOW
    pledge.resolved_at = now
    pledge.resolved_by = staff.id
    session.add(pledge)

    if donated:
        session.add(
            Donation(
                pledge_id=pledge.id,
                donor_id=pledge.donor_id,
                hospital_id=request.hospital_id,
                component_type_id=request.component_type_id,
                units=1,
                donated_at=now,
                confirmed_by=staff.id,
            )
        )
        donor = session.get(Donor, pledge.donor_id)
        if donor is not None:
            today = now.date()
            # Never move the date backwards if a later donation is already on record.
            if donor.last_donation_date is None or donor.last_donation_date < today:
                donor.last_donation_date = today
                session.add(donor)

    record_audit(
        session,
        actor=staff,
        action="pledge.donated" if donated else "pledge.no_show",
        entity_type="pledge",
        entity_id=pledge.id,
        before=before,
        after=_pledge_snapshot(pledge),
        ip_address=ip_address,
    )
    if not donated:
        _reopen_if_short(session, request, actor=None)

    session.commit()
    session.refresh(pledge)
    session.refresh(request)
    return PledgeOutcome(pledge=pledge, request=request)


@dataclass(frozen=True)
class HospitalPledgeView:
    """A pledge as hospital staff see it, with the donor's contact details."""

    pledge: Pledge
    donor: Donor
    user: User


def list_request_pledges(
    session: Session, request_id: UUID, hospital_id: UUID | None
) -> list[HospitalPledgeView]:
    """The pledges for one of the hospital's requests, oldest first.

    Raises:
        RequestNotFoundError: If the request does not exist or is not this hospital's.
    """
    request = session.get(BloodRequest, request_id)
    if request is None or hospital_id is None or request.hospital_id != hospital_id:
        raise RequestNotFoundError(str(request_id))

    rows = session.exec(
        select(Pledge, Donor, User)
        .join(Donor, col(Donor.id) == col(Pledge.donor_id))
        .join(User, col(User.id) == col(Donor.user_id))
        .where(Pledge.request_id == request_id)
        .order_by(col(Pledge.pledged_at), col(Pledge.id))
    ).all()
    return [HospitalPledgeView(pledge=p, donor=d, user=u) for p, d, u in rows]


@dataclass(frozen=True)
class DonorPledgeView:
    """A donor's own pledge with the request and hospital it is for."""

    pledge: Pledge
    request: BloodRequest
    hospital: Hospital
    component: ComponentType


def list_donor_pledges(
    session: Session, donor: Donor, *, limit: int, offset: int
) -> tuple[Sequence[DonorPledgeView], int]:
    """One page of the donor's pledges, most recent first, and the total number."""
    total = session.exec(
        select(func.count()).select_from(Pledge).where(Pledge.donor_id == donor.id)
    ).one()
    rows = session.exec(
        select(Pledge, BloodRequest, Hospital, ComponentType)
        .join(BloodRequest, col(BloodRequest.id) == col(Pledge.request_id))
        .join(Hospital, col(Hospital.id) == col(BloodRequest.hospital_id))
        .join(ComponentType, col(ComponentType.id) == col(BloodRequest.component_type_id))
        .where(Pledge.donor_id == donor.id)
        .order_by(col(Pledge.pledged_at).desc(), col(Pledge.id))
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        DonorPledgeView(pledge=p, request=r, hospital=h, component=c) for p, r, h, c in rows
    ], total
