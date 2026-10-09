"""Tests of a hospital's performance figures, against a real database.

Each figure is checked against a small, hand-countable set of requests and pledges, so the
expected value can be worked out on paper.
"""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import BloodRequest, Donation, Notification, Pledge
from app.models.base import utcnow
from app.models.enums import NotificationStatus, PledgeStatus, RequestStatus
from tests.helpers import (
    API,
    make_donor_record,
    make_request_record,
    make_staff_with_hospital,
    register_user,
    sign_in,
)

STATS = f"{API}/stats/hospital"


def aged_request(
    db_session: Session,
    hospital,
    staff,
    *,
    status: RequestStatus,
    age: timedelta = timedelta(days=1),
    fulfilled_after: timedelta | None = None,
    **kwargs,
) -> BloodRequest:
    """A request raised ``age`` ago, optionally fulfilled ``fulfilled_after`` it was raised."""
    request = make_request_record(db_session, hospital, staff, status=status, **kwargs)
    request.created_at = utcnow() - age
    if fulfilled_after is not None:
        request.fulfilled_at = request.created_at + fulfilled_after
    db_session.add(request)
    db_session.commit()
    db_session.refresh(request)
    return request


def pledges_with_outcomes(db_session: Session, request: BloodRequest, staff, statuses) -> None:
    """Add one pledge per status, from new donors; donated pledges get a donation row."""
    for number, status in enumerate(statuses):
        donor = make_donor_record(db_session, email=f"{request.id}-{number}@example.com")
        pledge = Pledge(request_id=request.id, donor_id=donor.id, status=status)
        db_session.add(pledge)
        db_session.commit()
        if status == PledgeStatus.DONATED:
            db_session.add(
                Donation(
                    pledge_id=pledge.id,
                    donor_id=donor.id,
                    hospital_id=request.hospital_id,
                    component_type_id=request.component_type_id,
                    units=1,
                    donated_at=utcnow(),
                    confirmed_by=staff.id,
                )
            )
            db_session.commit()


def test_a_new_hospital_has_zeros_and_no_rates(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _ = make_staff_with_hospital(db_session)
    sign_in(client, staff.email)

    body = client.get(STATS).json()

    assert body["period_days"] == 30
    assert body["requests_raised"] == 0
    # Nothing to measure yet: null, never a misleading 0%.
    assert body["fulfilment_rate"] is None
    assert body["median_minutes_to_fulfil"] is None
    assert body["no_show_rate"] is None


def test_fulfilment_rate_counts_finished_requests_that_met_every_unit(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = make_staff_with_hospital(db_session)
    aged_request(
        db_session,
        hospital,
        staff,
        status=RequestStatus.FULFILLED,
        fulfilled_after=timedelta(hours=1),
    )
    # Fulfilled first, closed afterwards: still a met request.
    aged_request(
        db_session, hospital, staff, status=RequestStatus.CLOSED, fulfilled_after=timedelta(hours=2)
    )
    aged_request(db_session, hospital, staff, status=RequestStatus.EXPIRED)
    # Still open: its outcome is not known, so it is left out of the rate.
    aged_request(db_session, hospital, staff, status=RequestStatus.OPEN)
    sign_in(client, staff.email)

    body = client.get(STATS).json()

    assert body["requests_raised"] == 4
    assert body["requests_open"] == 1
    assert body["requests_finished"] == 3
    assert body["requests_fulfilled"] == 2
    assert body["fulfilment_rate"] == 2 / 3


def test_median_time_to_fulfil_ignores_one_slow_request(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = make_staff_with_hospital(db_session)
    for minutes in (30, 90, 600):
        aged_request(
            db_session,
            hospital,
            staff,
            status=RequestStatus.FULFILLED,
            fulfilled_after=timedelta(minutes=minutes),
        )
    sign_in(client, staff.email)

    assert client.get(STATS).json()["median_minutes_to_fulfil"] == 90


def test_no_show_rate_counts_only_recorded_outcomes(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = make_staff_with_hospital(db_session)
    request = aged_request(db_session, hospital, staff, status=RequestStatus.OPEN, units_needed=10)
    pledges_with_outcomes(
        db_session,
        request,
        staff,
        [
            PledgeStatus.DONATED,
            PledgeStatus.DONATED,
            PledgeStatus.DONATED,
            PledgeStatus.NO_SHOW,
            # Not outcomes yet, so not part of the rate.
            PledgeStatus.PLEDGED,
            PledgeStatus.CANCELLED,
        ],
    )
    sign_in(client, staff.email)

    body = client.get(STATS).json()

    assert body["pledges_resolved"] == 4
    assert body["no_shows"] == 1
    assert body["no_show_rate"] == 0.25
    assert body["units_donated"] == 3


def test_only_requests_raised_in_the_period_count(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = make_staff_with_hospital(db_session)
    aged_request(db_session, hospital, staff, status=RequestStatus.EXPIRED, age=timedelta(days=5))
    aged_request(db_session, hospital, staff, status=RequestStatus.EXPIRED, age=timedelta(days=40))
    sign_in(client, staff.email)

    assert client.get(STATS).json()["requests_raised"] == 1
    assert client.get(STATS, params={"days": 90}).json()["requests_raised"] == 2


def test_an_overdue_request_counts_as_expired(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = make_staff_with_hospital(db_session)
    make_request_record(db_session, hospital, staff, deadline=utcnow() - timedelta(minutes=5))
    sign_in(client, staff.email)

    body = client.get(STATS).json()

    assert body["requests_open"] == 0
    assert body["requests_finished"] == 1
    assert body["fulfilment_rate"] == 0


def test_donors_alerted_counts_each_donor_once_and_only_delivered_messages(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = make_staff_with_hospital(db_session)
    first = aged_request(db_session, hospital, staff, status=RequestStatus.OPEN)
    second = aged_request(db_session, hospital, staff, status=RequestStatus.OPEN)
    reached = make_donor_record(db_session, email="reached@example.com")
    missed = make_donor_record(db_session, email="missed@example.com")
    db_session.add_all(
        [
            Notification(request_id=first.id, donor_id=reached.id, status=NotificationStatus.SENT),
            Notification(request_id=second.id, donor_id=reached.id, status=NotificationStatus.SENT),
            Notification(request_id=first.id, donor_id=missed.id, status=NotificationStatus.FAILED),
        ]
    )
    db_session.commit()
    sign_in(client, staff.email)

    assert client.get(STATS).json()["donors_alerted"] == 1


def test_another_hospitals_activity_is_not_counted(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _ = make_staff_with_hospital(db_session)
    other, other_hospital = make_staff_with_hospital(
        db_session, email="other@example.com", name="Other"
    )
    aged_request(db_session, other_hospital, other, status=RequestStatus.EXPIRED)
    sign_in(client, staff.email)

    assert client.get(STATS).json()["requests_raised"] == 0


def test_staff_without_a_hospital_are_told_to_register(
    client: TestClient, db_session: Session
) -> None:
    register_user(client, email="new-staff@example.com", role="hospital_staff")

    assert client.get(STATS).status_code == 404


def test_donors_cannot_read_hospital_figures(client: TestClient, db_session: Session) -> None:
    register_user(client, email="donor@example.com", role="donor")

    assert client.get(STATS).status_code == 403


def test_the_period_is_limited_to_a_year(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _ = make_staff_with_hospital(db_session)
    sign_in(client, staff.email)

    assert client.get(STATS, params={"days": 366}).status_code == 422
    assert client.get(STATS, params={"days": 0}).status_code == 422
