"""Tests of the blood request endpoints against a real database."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import AuditLog, BloodRequest, Pledge
from app.models.base import utcnow
from app.models.enums import (
    BloodGroup,
    PledgeStatus,
    RequestStatus,
    VerificationStatus,
)
from app.services.requests import MAX_OPEN_REQUESTS_PER_HOSPITAL
from tests.helpers import (
    API,
    make_donor_record,
    make_request_record,
    make_staff_with_hospital,
    register_user,
    request_payload,
    sign_in,
)

REQUESTS = f"{API}/requests"


def signed_in_staff(client: TestClient, db_session: Session, **kwargs):
    """Create a staff member with a hospital and sign the client in as them."""
    staff, hospital = make_staff_with_hospital(db_session, **kwargs)
    sign_in(client, staff.email)
    return staff, hospital


# ---------------------------------------------------------------------------------------
# Raising a request
# ---------------------------------------------------------------------------------------


def test_a_verified_hospital_can_raise_a_request(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    signed_in_staff(client, db_session)

    response = client.post(REQUESTS, json=request_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["recipient_group"] == "O-"
    assert body["component_code"] == "whole_blood"
    assert body["component_name"] == "Whole blood"
    assert body["units_needed"] == 2
    assert body["units_pledged"] == 0
    assert body["units_remaining"] == 2


def test_raising_a_request_is_recorded_in_the_audit_log(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _ = signed_in_staff(client, db_session)
    created = client.post(REQUESTS, json=request_payload()).json()

    entry = db_session.exec(select(AuditLog).where(AuditLog.action == "request.created")).one()

    assert str(entry.entity_id) == created["id"]
    assert entry.actor_user_id == staff.id
    assert entry.after["units_needed"] == 2


def test_a_blank_note_is_stored_as_nothing(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    signed_in_staff(client, db_session)

    response = client.post(REQUESTS, json=request_payload(notes="   "))

    assert response.json()["notes"] is None


def test_unverified_hospitals_cannot_raise_requests(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    signed_in_staff(client, db_session, status=VerificationStatus.PENDING)

    assert client.post(REQUESTS, json=request_payload()).status_code == 403


def test_staff_without_a_hospital_cannot_raise_requests(
    client: TestClient, reference_data: None
) -> None:
    register_user(client, email="staff1@example.com", role="hospital_staff")

    assert client.post(REQUESTS, json=request_payload()).status_code == 403


def test_donors_and_visitors_cannot_raise_requests(
    client: TestClient, reference_data: None
) -> None:
    assert client.post(REQUESTS, json=request_payload()).status_code == 401
    register_user(client, email="donor1@example.com", role="donor")
    assert client.post(REQUESTS, json=request_payload()).status_code == 403


# ---------------------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------------------


def test_the_number_of_units_must_be_sensible(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    signed_in_staff(client, db_session)

    assert client.post(REQUESTS, json=request_payload(units_needed=0)).status_code == 422
    assert client.post(REQUESTS, json=request_payload(units_needed=21)).status_code == 422
    assert client.post(REQUESTS, json=request_payload(units_needed=20)).status_code == 201


def test_a_deadline_in_the_past_is_rejected(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    signed_in_staff(client, db_session)
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()

    assert client.post(REQUESTS, json=request_payload(deadline=past)).status_code == 422


def test_a_deadline_without_a_time_zone_is_rejected(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    signed_in_staff(client, db_session)
    naive = (datetime.now(UTC) + timedelta(days=1)).replace(tzinfo=None).isoformat()

    assert client.post(REQUESTS, json=request_payload(deadline=naive)).status_code == 422


def test_a_deadline_too_far_away_is_rejected(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    signed_in_staff(client, db_session)
    far = (datetime.now(UTC) + timedelta(days=31)).isoformat()

    assert client.post(REQUESTS, json=request_payload(deadline=far)).status_code == 422


def test_an_unknown_component_is_rejected(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    signed_in_staff(client, db_session)

    response = client.post(REQUESTS, json=request_payload(component_code="unicorn_blood"))

    assert response.status_code == 422


def test_a_hospital_cannot_exceed_its_limit_of_open_requests(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    for _ in range(MAX_OPEN_REQUESTS_PER_HOSPITAL):
        make_request_record(db_session, hospital, staff)

    assert client.post(REQUESTS, json=request_payload()).status_code == 409


# ---------------------------------------------------------------------------------------
# Reading and ownership
# ---------------------------------------------------------------------------------------


def test_the_list_shows_only_the_hospitals_own_requests_newest_first(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    other_staff, other_hospital = make_staff_with_hospital(
        db_session, email="staff2@example.com", name="Other Hospital"
    )
    first = make_request_record(db_session, hospital, staff, units_needed=1)
    second = make_request_record(db_session, hospital, staff, units_needed=2)
    make_request_record(db_session, other_hospital, other_staff)

    page = client.get(REQUESTS).json()

    assert page["total"] == 2
    assert [item["id"] for item in page["items"]] == [str(second.id), str(first.id)]


def test_the_list_can_be_filtered_by_status_and_paged(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    for _ in range(3):
        make_request_record(db_session, hospital, staff)
    make_request_record(db_session, hospital, staff, status=RequestStatus.CLOSED)

    open_only = client.get(REQUESTS, params={"status": "open"}).json()
    paged = client.get(REQUESTS, params={"limit": 2, "offset": 2}).json()

    assert open_only["total"] == 3
    assert paged["total"] == 4
    assert len(paged["items"]) == 2


def test_one_request_can_be_read_by_its_hospital(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    request = make_request_record(db_session, hospital, staff)

    response = client.get(f"{REQUESTS}/{request.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(request.id)


def test_another_hospitals_request_is_reported_as_not_found(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    other_staff, other_hospital = make_staff_with_hospital(
        db_session, email="staff2@example.com", name="Other Hospital"
    )
    foreign = make_request_record(db_session, other_hospital, other_staff)
    signed_in_staff(client, db_session)

    assert client.get(f"{REQUESTS}/{foreign.id}").status_code == 404
    assert client.post(f"{REQUESTS}/{foreign.id}/close").status_code == 404
    assert client.get(f"{REQUESTS}/{foreign.id}/matches").status_code == 404
    assert client.get(f"{REQUESTS}/{uuid4()}").status_code == 404


def test_pledged_units_are_counted(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    request = make_request_record(db_session, hospital, staff, units_needed=3)
    donor = make_donor_record(db_session, email="donor1@example.com")
    cancelled_donor = make_donor_record(db_session, email="donor2@example.com")
    db_session.add(Pledge(request_id=request.id, donor_id=donor.id, status=PledgeStatus.PLEDGED))
    db_session.add(
        Pledge(request_id=request.id, donor_id=cancelled_donor.id, status=PledgeStatus.CANCELLED)
    )
    db_session.commit()

    body = client.get(f"{REQUESTS}/{request.id}").json()

    assert body["units_pledged"] == 1
    assert body["units_remaining"] == 2


# ---------------------------------------------------------------------------------------
# Closing and expiry
# ---------------------------------------------------------------------------------------


def test_a_request_can_be_closed_once(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    request = make_request_record(db_session, hospital, staff)

    first = client.post(f"{REQUESTS}/{request.id}/close")
    second = client.post(f"{REQUESTS}/{request.id}/close")

    assert first.status_code == 200
    assert first.json()["status"] == "closed"
    assert second.status_code == 409
    closed = db_session.exec(select(AuditLog).where(AuditLog.action == "request.closed")).all()
    assert len(closed) == 1


def test_an_overdue_request_is_shown_as_expired_and_the_change_is_saved(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    request = make_request_record(
        db_session, hospital, staff, deadline=utcnow() - timedelta(hours=1)
    )

    body = client.get(f"{REQUESTS}/{request.id}").json()

    assert body["status"] == "expired"
    db_session.expire_all()
    assert db_session.get(BloodRequest, request.id).status == RequestStatus.EXPIRED
    entry = db_session.exec(select(AuditLog).where(AuditLog.action == "request.expired")).one()
    assert entry.actor_user_id is None


def test_the_list_also_expires_overdue_requests(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    make_request_record(db_session, hospital, staff, deadline=utcnow() - timedelta(minutes=1))
    make_request_record(db_session, hospital, staff)

    open_only = client.get(REQUESTS, params={"status": "open"}).json()
    expired = client.get(REQUESTS, params={"status": "expired"}).json()

    assert open_only["total"] == 1
    assert expired["total"] == 1


def test_an_expired_request_cannot_be_closed(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    request = make_request_record(
        db_session, hospital, staff, deadline=utcnow() - timedelta(hours=1)
    )

    assert client.post(f"{REQUESTS}/{request.id}/close").status_code == 409


# ---------------------------------------------------------------------------------------
# Matches
# ---------------------------------------------------------------------------------------


def test_matches_are_ranked_nearest_first_and_anonymous(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    request = make_request_record(db_session, hospital, staff)
    for city, offset in (("Far", 0.15), ("Near", 0.05)):
        make_donor_record(
            db_session,
            email=f"{city}@example.com",
            city=city,
            latitude=hospital.latitude + offset,
        )

    body = client.get(f"{REQUESTS}/{request.id}/matches").json()

    assert [item["city"] for item in body["items"]] == ["Near", "Far"]
    assert body["total"] == 2
    assert body["radius_km"] == 25
    # Only these fields: no name, email, phone or exact location.
    assert set(body["items"][0]) == {"donor_id", "blood_group", "city", "distance_km"}


def test_the_radius_can_be_widened_but_not_beyond_the_maximum(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    request = make_request_record(db_session, hospital, staff)
    make_donor_record(db_session, email="far@example.com", latitude=hospital.latitude + 0.6)
    url = f"{REQUESTS}/{request.id}/matches"

    assert client.get(url).json()["total"] == 0
    assert client.get(url, params={"radius_km": 100}).json()["total"] == 1
    assert client.get(url, params={"radius_km": 0}).status_code == 422
    assert client.get(url, params={"radius_km": 500}).status_code == 422


def test_matches_are_only_available_for_open_requests(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital = signed_in_staff(client, db_session)
    request = make_request_record(
        db_session, hospital, staff, recipient_group=BloodGroup.A_POSITIVE
    )
    client.post(f"{REQUESTS}/{request.id}/close")

    assert client.get(f"{REQUESTS}/{request.id}/matches").status_code == 409
