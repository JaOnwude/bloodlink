"""Pledges made at the same instant, against a real PostgreSQL database.

This is the second hard part of the project: a request is never promised more units than
it needs, even when donors accept simultaneously. Each test starts several threads, each
with its own database connection, holds them at a barrier, and releases them together,
so the pledges really do compete for the request's row lock.

Without the lock taken in ``create_pledge``, these tests fail: every thread counts the
pledges before any of them has committed, sees a free unit, and inserts its own.
"""

import threading
from uuid import UUID

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.models import BloodRequest, Donor, Pledge, User
from app.models.enums import PledgeStatus, RequestStatus
from app.services.pledges import (
    AlreadyPledgedError,
    RequestFullError,
    RequestNotOpenError,
    create_pledge,
)
from tests.helpers import make_donor_record, make_request_record, make_staff_with_hospital


def race(engine: Engine, request_id: UUID, donor_ids: list[UUID]) -> list[str]:
    """Pledge every donor to the request at the same moment and report each outcome.

    Each outcome is ``"accepted"`` or the name of the exception that refused the pledge.
    """
    barrier = threading.Barrier(len(donor_ids))
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt(donor_id: UUID) -> None:
        with Session(engine) as session:
            donor = session.get(Donor, donor_id)
            assert donor is not None
            user = session.get(User, donor.user_id)
            assert user is not None
            barrier.wait()
            try:
                create_pledge(session, user, donor, request_id, ip_address=None)
                result = "accepted"
            except (RequestFullError, AlreadyPledgedError, RequestNotOpenError) as exc:
                result = type(exc).__name__
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt, args=(donor_id,)) for donor_id in donor_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert all(not thread.is_alive() for thread in threads), "a pledge never finished"
    return outcomes


def make_donors(db_session: Session, count: int) -> list[UUID]:
    return [make_donor_record(db_session, email=f"racer{n}@example.com").id for n in range(count)]


def counted_pledges(db_session: Session, request_id: UUID) -> int:
    return len(
        db_session.exec(
            select(Pledge).where(
                Pledge.request_id == request_id, Pledge.status == PledgeStatus.PLEDGED
            )
        ).all()
    )


def test_two_donors_racing_for_the_last_unit_produce_one_success_and_one_refusal(
    db_engine: Engine, db_session: Session, reference_data: None
) -> None:
    staff, hospital = make_staff_with_hospital(db_session)
    request = make_request_record(db_session, hospital, staff, units_needed=1)
    donors = make_donors(db_session, 2)

    outcomes = race(db_engine, request.id, donors)

    assert sorted(outcomes) == ["RequestFullError", "accepted"]
    db_session.expire_all()
    assert counted_pledges(db_session, request.id) == 1
    assert db_session.get(BloodRequest, request.id).status == RequestStatus.FULFILLED


def test_many_donors_racing_never_exceed_the_units_needed(
    db_engine: Engine, db_session: Session, reference_data: None
) -> None:
    staff, hospital = make_staff_with_hospital(db_session)
    request = make_request_record(db_session, hospital, staff, units_needed=3)
    donors = make_donors(db_session, 10)

    outcomes = race(db_engine, request.id, donors)

    assert outcomes.count("accepted") == 3
    assert outcomes.count("RequestFullError") == 7
    db_session.expire_all()
    assert counted_pledges(db_session, request.id) == 3
    assert db_session.get(BloodRequest, request.id).status == RequestStatus.FULFILLED


def test_one_donor_submitting_twice_at_once_gets_one_pledge(
    db_engine: Engine, db_session: Session, reference_data: None
) -> None:
    staff, hospital = make_staff_with_hospital(db_session)
    request = make_request_record(db_session, hospital, staff, units_needed=5)
    [donor_id] = make_donors(db_session, 1)

    outcomes = race(db_engine, request.id, [donor_id, donor_id])

    assert sorted(outcomes) == ["AlreadyPledgedError", "accepted"]
    db_session.expire_all()
    assert counted_pledges(db_session, request.id) == 1
