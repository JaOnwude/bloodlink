"""Tests of standby donors and screening outcomes, against a real database.

A pledge is not a unit of blood: some donors are turned away at screening and some do not
come. These tests check that a request can hold donors in reserve without ever counting
them against the units it needs, that a freed unit goes to the longest-waiting standby
donor (who is told), that reserve donors are released once they cannot be needed, and that
a deferral at screening is recorded for the right period without revealing its reason.
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

import app.services.notifications as notifications
from app.models import BloodRequest, Donor, DonorDeferral, Pledge, User
from app.models.enums import PledgeStatus, RequestStatus
from app.services.requests import expire_overdue
from app.services.sms import SmsResult
from tests.helpers import (
    API,
    make_donor_record,
    make_request_record,
    make_signed_in_donor,
    make_staff_with_hospital,
    sign_in,
)
from tests.test_pledge_concurrency import race


class RecordingSender:
    """Accepts every message and remembers it."""

    name = "recording"

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, to: str, text: str) -> SmsResult:
        self.sent.append((to, text))
        return SmsResult(ok=True, message_id=f"msg-{len(self.sent)}")


@pytest.fixture
def sender(monkeypatch: pytest.MonkeyPatch) -> RecordingSender:
    """Route every message sent through the API to a recording sender."""
    recording = RecordingSender()
    monkeypatch.setattr(notifications, "get_sms_sender", lambda settings=None: recording)
    return recording


def pledge(client: TestClient, request_id) -> object:
    return client.post(f"{API}/requests/{request_id}/pledges")


def setup(db_session: Session, **overrides):
    """A verified hospital with one O- request for one unit and one standby place."""
    staff, hospital = make_staff_with_hospital(db_session)
    values = {"units_needed": 1, "standby_units": 1, **overrides}
    request = make_request_record(db_session, hospital, staff, **values)
    return staff, hospital, request


def pledge_as(client: TestClient, email: str, request_id, **profile) -> dict:
    """Register a donor, pledge them to the request, and return the response body."""
    make_signed_in_donor(client, email=email, **profile)
    response = pledge(client, request_id)
    assert response.status_code == 201, response.text
    return response.json()


def status_of(db_session: Session, pledge_id) -> PledgeStatus:
    db_session.expire_all()
    return db_session.get(Pledge, pledge_id).status


# ---------------------------------------------------------------------------------------
# Joining the reserve
# ---------------------------------------------------------------------------------------


def test_once_every_unit_is_pledged_donors_join_the_standby_reserve(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)

    first = pledge_as(client, "first@example.com", request.id)
    second = pledge_as(client, "second@example.com", request.id)
    make_signed_in_donor(client, email="third@example.com")
    third = pledge(client, request.id)

    assert first["status"] == "pledged"
    assert first["request_status"] == "fulfilled"
    assert second["status"] == "standby"
    assert second["standby_places_left"] == 0
    assert third.status_code == 409
    assert "standby place" in third.json()["detail"]


def test_standby_donors_never_count_against_the_units_needed(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup(db_session, units_needed=2, standby_units=2)
    for number in range(4):
        pledge_as(client, f"d{number}@example.com", request.id)

    sign_in(client, staff.email)
    body = client.get(f"{API}/requests/{request.id}").json()

    assert body["units_pledged"] == 2
    assert body["units_remaining"] == 0
    assert body["standby_units"] == 2
    assert body["standby_pledged"] == 2


def test_without_standby_places_a_full_request_refuses_as_before(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session, standby_units=0)
    pledge_as(client, "first@example.com", request.id)
    make_signed_in_donor(client, email="second@example.com")

    response = pledge(client, request.id)

    assert response.status_code == 409
    assert response.json()["detail"] == "Every unit this request needs has already been pledged."


def test_a_donor_on_standby_cannot_pledge_to_another_request(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital, request = setup(db_session)
    other = make_request_record(db_session, hospital, staff)
    pledge_as(client, "first@example.com", request.id)
    pledge_as(client, "second@example.com", request.id)

    response = pledge(client, other.id)

    assert response.status_code == 409
    assert "another request" in response.json()["detail"]


def test_many_donors_racing_never_exceed_the_units_or_the_standby_places(
    db_engine: Engine, db_session: Session, reference_data: None
) -> None:
    staff, hospital = make_staff_with_hospital(db_session)
    request = make_request_record(db_session, hospital, staff, units_needed=2, standby_units=3)
    racers = [make_donor_record(db_session, email=f"r{n}@example.com").id for n in range(12)]
    request_id = request.id

    outcomes = race(db_engine, request_id, racers)

    # 2 units and 3 standby places: exactly 5 accepted, whatever the order of arrival.
    assert outcomes.count("accepted") == 5
    assert outcomes.count("RequestFullError") == 7
    db_session.expire_all()
    by_status = [
        pledge.status
        for pledge in db_session.exec(select(Pledge).where(Pledge.request_id == request_id))
    ]
    assert by_status.count(PledgeStatus.PLEDGED) == 2
    assert by_status.count(PledgeStatus.STANDBY) == 3


# ---------------------------------------------------------------------------------------
# Promotion when a unit is freed
# ---------------------------------------------------------------------------------------


def test_a_no_show_promotes_the_standby_donor_and_texts_them(
    client: TestClient, db_session: Session, reference_data: None, sender: RecordingSender
) -> None:
    staff, hospital, request = setup(db_session)
    first = pledge_as(client, "first@example.com", request.id)
    second = pledge_as(client, "second@example.com", request.id)
    # Give the standby donor a phone so the promotion message can reach them.
    db_session.expire_all()
    standby_donor = db_session.get(Donor, db_session.get(Pledge, second["id"]).donor_id)
    user = db_session.get(User, standby_donor.user_id)
    user.phone = "+2348000000002"
    db_session.add(user)
    db_session.commit()

    sign_in(client, staff.email)
    response = client.post(f"{API}/pledges/{first['id']}/no-show")

    assert response.status_code == 200
    # The unit was refilled from standby, so the request stays fulfilled.
    assert response.json()["request_status"] == "fulfilled"
    assert response.json()["units_remaining"] == 0
    assert status_of(db_session, second["id"]) == PledgeStatus.PLEDGED
    [(to, text)] = sender.sent
    assert to == "+2348000000002"
    assert "you are now needed" in text
    assert hospital.name in text


def test_cancelling_a_pledge_promotes_the_longest_waiting_standby_donor(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session, standby_units=2)
    first = pledge_as(client, "first@example.com", request.id)
    earlier = pledge_as(client, "earlier@example.com", request.id)
    later = pledge_as(client, "later@example.com", request.id)

    sign_in(client, "first@example.com")
    client.delete(f"{API}/pledges/{first['id']}")

    assert status_of(db_session, earlier["id"]) == PledgeStatus.PLEDGED
    assert status_of(db_session, later["id"]) == PledgeStatus.STANDBY


def test_a_standby_donor_stepping_down_frees_only_their_place(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)
    first = pledge_as(client, "first@example.com", request.id)
    second = pledge_as(client, "second@example.com", request.id)

    response = client.delete(f"{API}/pledges/{second['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["standby_places_left"] == 1
    assert status_of(db_session, first["id"]) == PledgeStatus.PLEDGED


def test_with_nobody_on_standby_a_freed_unit_reopens_the_request(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup(db_session)
    first = pledge_as(client, "first@example.com", request.id)

    sign_in(client, staff.email)
    response = client.post(f"{API}/pledges/{first['id']}/no-show")

    assert response.json()["request_status"] == "open"


def test_an_outcome_cannot_be_recorded_for_a_donor_still_on_standby(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup(db_session)
    pledge_as(client, "first@example.com", request.id)
    second = pledge_as(client, "second@example.com", request.id)

    sign_in(client, staff.email)
    response = client.post(f"{API}/pledges/{second['id']}/donated")

    assert response.status_code == 409
    assert "standby" in response.json()["detail"]


# ---------------------------------------------------------------------------------------
# Releasing the reserve
# ---------------------------------------------------------------------------------------


def test_standby_donors_are_released_once_every_unit_is_given(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital, request = setup(db_session)
    first = pledge_as(client, "first@example.com", request.id)
    second = pledge_as(client, "second@example.com", request.id)

    sign_in(client, staff.email)
    client.post(f"{API}/pledges/{first['id']}/donated")

    assert status_of(db_session, second["id"]) == PledgeStatus.RELEASED
    # Released, the donor is free to answer another request.
    another = make_request_record(db_session, hospital, staff)
    sign_in(client, "second@example.com")
    assert pledge(client, another.id).status_code == 201


def test_closing_a_request_releases_its_standby_donors(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup(db_session)
    pledge_as(client, "first@example.com", request.id)
    second = pledge_as(client, "second@example.com", request.id)

    sign_in(client, staff.email)
    client.post(f"{API}/requests/{request.id}/close")

    assert status_of(db_session, second["id"]) == PledgeStatus.RELEASED


def test_standby_donors_are_released_when_a_fulfilled_requests_deadline_passes(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session)
    pledge_as(client, "first@example.com", request.id)
    second = pledge_as(client, "second@example.com", request.id)

    expire_overdue(db_session, now=datetime.now(UTC) + timedelta(days=2))

    assert status_of(db_session, second["id"]) == PledgeStatus.RELEASED
    db_session.expire_all()
    # A fulfilled request keeps its state; only the reserve is released.
    assert db_session.get(BloodRequest, request.id).status == RequestStatus.FULFILLED


def test_a_released_donors_contact_details_are_withheld(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup(db_session)
    pledge_as(client, "first@example.com", request.id)
    pledge_as(client, "second@example.com", request.id)
    sign_in(client, staff.email)
    client.post(f"{API}/requests/{request.id}/close")

    items = client.get(f"{API}/requests/{request.id}/pledges").json()

    released = next(item for item in items if item["status"] == "released")
    assert released["donor"]["email"] is None
    assert released["donor"]["phone"] is None


# ---------------------------------------------------------------------------------------
# Deferral at screening
# ---------------------------------------------------------------------------------------


def test_a_deferral_defers_the_donor_for_the_reasons_period_and_promotes_standby(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup(db_session)
    first = pledge_as(client, "first@example.com", request.id)
    second = pledge_as(client, "second@example.com", request.id)

    sign_in(client, staff.email)
    response = client.post(
        f"{API}/pledges/{first['id']}/deferred", json={"reason": "low_haemoglobin"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "deferred"
    assert status_of(db_session, second["id"]) == PledgeStatus.PLEDGED
    first_donor = db_session.get(Pledge, first["id"]).donor_id
    [deferral] = db_session.exec(
        select(DonorDeferral).where(DonorDeferral.donor_id == first_donor)
    ).all()
    assert deferral.deferred_until == datetime.now(UTC).date() + timedelta(days=90)
    assert deferral.recorded_by == staff.id
    # The hospital that recorded it sees the reason.
    [mine] = [
        item
        for item in client.get(f"{API}/requests/{request.id}/pledges").json()
        if item["id"] == first["id"]
    ]
    assert mine["deferral_reason"] == "low_haemoglobin"


def test_a_deferred_donor_is_told_what_to_do_and_cannot_give_meanwhile(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital, request = setup(db_session)
    first = pledge_as(client, "first@example.com", request.id)
    sign_in(client, staff.email)
    client.post(f"{API}/pledges/{first['id']}/deferred", json={"reason": "low_haemoglobin"})
    another = make_request_record(db_session, hospital, staff)

    sign_in(client, "first@example.com")
    [item] = client.get(f"{API}/donors/me/pledges").json()["items"]
    eligibility = client.get(f"{API}/donors/me/eligibility").json()

    assert item["status"] == "deferred"
    assert "iron-rich" in item["outcome_message"]
    assert eligibility["eligible_for_any"] is False
    assert pledge(client, another.id).status_code == 403


def test_a_positive_screen_defers_permanently_and_is_never_revealed_to_the_donor(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup(db_session)
    first = pledge_as(client, "first@example.com", request.id)
    sign_in(client, staff.email)
    client.post(f"{API}/pledges/{first['id']}/deferred", json={"reason": "positive_screen"})

    first_donor = db_session.get(Pledge, first["id"]).donor_id
    [deferral] = db_session.exec(
        select(DonorDeferral).where(DonorDeferral.donor_id == first_donor)
    ).all()
    sign_in(client, "first@example.com")
    history = client.get(f"{API}/donors/me/pledges").text

    assert deferral.deferred_until is None
    assert "contact the hospital" in history
    assert "positive" not in history.lower()
    assert "infection" not in history.lower()


def test_a_deferral_needs_a_known_reason(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup(db_session)
    first = pledge_as(client, "first@example.com", request.id)
    sign_in(client, staff.email)

    missing = client.post(f"{API}/pledges/{first['id']}/deferred", json={})
    unknown = client.post(f"{API}/pledges/{first['id']}/deferred", json={"reason": "bad_day"})

    assert missing.status_code == 422
    assert unknown.status_code == 422
    assert status_of(db_session, first["id"]) == PledgeStatus.PLEDGED


def test_staff_can_list_the_deferral_reasons_with_their_periods(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _ = make_staff_with_hospital(db_session)
    sign_in(client, staff.email)

    reasons = {item["code"]: item for item in client.get(f"{API}/deferral-reasons").json()}

    assert set(reasons) == {
        "low_haemoglobin",
        "blood_pressure",
        "recent_illness",
        "medication",
        "positive_screen",
        "other",
    }
    assert reasons["positive_screen"]["deferral_days"] is None
    assert reasons["low_haemoglobin"]["deferral_days"] == 90
    # Every option is distinct, so staff cannot confuse one reason with another.
    labels = [item["label"] for item in reasons.values()]
    assert len(set(labels)) == len(labels)
    assert "Positive infection screen" in reasons["positive_screen"]["label"]


def test_donors_cannot_list_or_record_deferrals(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)
    first = pledge_as(client, "first@example.com", request.id)

    assert client.get(f"{API}/deferral-reasons").status_code == 403
    response = client.post(f"{API}/pledges/{first['id']}/deferred", json={"reason": "other"})
    assert response.status_code == 403


# ---------------------------------------------------------------------------------------
# What donors and hospitals see
# ---------------------------------------------------------------------------------------


def test_a_fulfilled_request_with_standby_places_is_offered_to_donors(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)
    pledge_as(client, "first@example.com", request.id)

    make_signed_in_donor(client, email="second@example.com")
    [item] = client.get(f"{API}/donors/me/requests").json()["items"]
    assert item["id"] == str(request.id)
    assert item["units_remaining"] == 0
    assert item["standby_places_left"] == 1
    assert item["my_pledge_id"] is None

    pledge(client, request.id)
    [item] = client.get(f"{API}/donors/me/requests").json()["items"]
    assert item["my_pledge_status"] == "standby"


def test_standby_donors_are_left_out_of_other_hospitals_matches(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)
    pledge_as(client, "first@example.com", request.id)
    pledge_as(client, "second@example.com", request.id)
    other_staff, other_hospital = make_staff_with_hospital(
        db_session, email="other@example.com", name="Other"
    )
    other_request = make_request_record(db_session, other_hospital, other_staff)

    sign_in(client, other_staff.email)
    body = client.get(f"{API}/requests/{other_request.id}/matches").json()

    assert body["total"] == 0
