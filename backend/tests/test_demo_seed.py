"""Tests of the demonstration data loader against a real database.

The demonstration is what assessors see first, so these check that it is complete (every
role can sign in, every review state and request state is represented), that it obeys the
same rules as the application (no request is over-pledged, a confirmed donation starts the
waiting period), that the open requests actually find donors, and that it cannot reach a
stranger's phone.
"""

from collections import Counter
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlmodel import Session, col, select

from app.db.demo_seed import (
    ADMIN_EMAIL,
    DEMO_DOMAIN,
    DemoSummary,
    donor_email,
    seed_demo_data,
    staff_email,
)
from app.models import BloodRequest, Donation, Donor, Hospital, Pledge, User
from app.models.enums import (
    BloodGroup,
    PledgeStatus,
    RequestStatus,
    RequestUrgency,
    VerificationStatus,
)
from app.services.matching import find_matches
from tests.helpers import API, PASSWORD

PHONE = "+2348011112222"


@pytest.fixture
def summary(db_session: Session) -> DemoSummary:
    """Seed the demonstration data once for the test, with a phone for donor01."""
    return seed_demo_data(db_session, password=PASSWORD, donor_phone=PHONE)


def test_seeding_reports_what_it_created(summary: DemoSummary) -> None:
    assert summary.created is True
    # 1 administrator, 5 staff and 28 donors.
    assert summary.users == 34
    assert summary.hospitals == 5
    assert summary.donors == 28
    assert summary.requests == 6
    assert summary.pledges == 3
    assert summary.donations == 1


def test_seeding_twice_changes_nothing(db_session: Session, summary: DemoSummary) -> None:
    users_before = db_session.exec(select(func.count()).select_from(User)).one()

    again = seed_demo_data(db_session, password=PASSWORD)

    assert again.created is False
    assert db_session.exec(select(func.count()).select_from(User)).one() == users_before
    assert again.requests == summary.requests


def test_every_review_state_is_represented(db_session: Session, summary: DemoSummary) -> None:
    states = Counter(h.verification_status for h in db_session.exec(select(Hospital)).all())

    assert states == {
        VerificationStatus.VERIFIED: 3,
        VerificationStatus.PENDING: 1,
        VerificationStatus.REJECTED: 1,
    }
    rejected = db_session.exec(
        select(Hospital).where(Hospital.verification_status == VerificationStatus.REJECTED)
    ).one()
    assert rejected.rejection_reason


def test_every_request_state_is_represented(db_session: Session, summary: DemoSummary) -> None:
    states = Counter(r.status for r in db_session.exec(select(BloodRequest)).all())

    assert states[RequestStatus.OPEN] == 4
    assert states[RequestStatus.FULFILLED] == 1
    assert states[RequestStatus.EXPIRED] == 1


@pytest.mark.parametrize(
    "email",
    [ADMIN_EMAIL, staff_email("lagos"), staff_email("pending"), donor_email(1), donor_email(28)],
)
def test_each_kind_of_account_can_sign_in(
    client: TestClient, summary: DemoSummary, email: str
) -> None:
    response = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200, response.text


def test_no_request_is_promised_more_units_than_it_needs(
    db_session: Session, summary: DemoSummary
) -> None:
    for request in db_session.exec(select(BloodRequest)).all():
        taken = db_session.exec(
            select(func.count())
            .select_from(Pledge)
            .where(
                Pledge.request_id == request.id,
                col(Pledge.status).in_((PledgeStatus.PLEDGED, PledgeStatus.DONATED)),
            )
        ).one()
        assert taken <= request.units_needed


def test_the_confirmed_donation_started_the_donors_waiting_period(
    db_session: Session, summary: DemoSummary
) -> None:
    donation = db_session.exec(select(Donation)).one()
    donor = db_session.get(Donor, donation.donor_id)

    assert donor is not None
    assert donor.last_donation_date == datetime.now(UTC).date()


def test_the_critical_request_finds_donor01_among_its_matches(
    db_session: Session, summary: DemoSummary
) -> None:
    request = db_session.exec(
        select(BloodRequest).where(BloodRequest.urgency == RequestUrgency.CRITICAL)
    ).one()
    hospital = db_session.get(Hospital, request.hospital_id)
    donor01 = db_session.exec(select(Donor).join(User).where(User.email == donor_email(1))).one()

    matches, total = find_matches(db_session, request, hospital, radius_km=25, limit=50)

    assert request.recipient_group == BloodGroup.O_NEGATIVE
    assert total >= 1
    assert donor01.id in {match.donor.id for match in matches}


def test_every_open_request_has_at_least_one_match(
    db_session: Session, summary: DemoSummary
) -> None:
    open_requests = db_session.exec(
        select(BloodRequest).where(BloodRequest.status == RequestStatus.OPEN)
    ).all()

    for request in open_requests:
        hospital = db_session.get(Hospital, request.hospital_id)
        _, total = find_matches(db_session, request, hospital, radius_km=25, limit=50)
        assert total >= 1, f"{request.recipient_group} request in {hospital.city} has no match"


def test_only_donor01_has_a_phone_number(db_session: Session, summary: DemoSummary) -> None:
    phones = {
        user.email: user.phone
        for user in db_session.exec(
            select(User).where(col(User.email).endswith(f"@{DEMO_DOMAIN}"))
        ).all()
    }

    assert phones.pop(donor_email(1)) == PHONE
    assert all(phone is None for phone in phones.values())


def test_without_a_phone_no_donor_can_be_texted(db_session: Session) -> None:
    seed_demo_data(db_session, password=PASSWORD)

    with_phone = db_session.exec(
        select(User).where(User.role == "donor", col(User.phone).is_not(None))
    ).all()
    assert with_phone == []
