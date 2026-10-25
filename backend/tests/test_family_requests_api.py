"""Tests of families asking a hospital for blood, and staff answering, against a real database."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import AuditLog, BloodRequest, FamilyRequest
from app.models.enums import FamilyRequestStatus, RequestStatus, VerificationStatus
from app.services.family_requests import MAX_PENDING_PER_PHONE
from tests.helpers import API, make_staff_with_hospital, register_user, sign_in

PUBLIC_HOSPITALS = f"{API}/public/hospitals"
STAFF = f"{API}/family-requests"


def appeal_payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "requester_name": "Ngozi Okafor",
        "requester_phone": "+2348031112222",
        "recipient_group": "O+",
        "component_code": "whole_blood",
        "units_needed": 2,
        "ward_reference": "Maternity ward, bed 4",
        "notes": "Doctor said before tomorrow morning",
        "patient_is_admitted": True,
    }
    body.update(overrides)
    return body


def approve_payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "urgency": "urgent",
        "deadline": (datetime.now(UTC) + timedelta(hours=12)).isoformat(),
    }
    body.update(overrides)
    return body


def _hospital(db_session: Session, **fields: object):
    staff, hospital = make_staff_with_hospital(db_session, **fields)
    return staff, hospital


def _send(client: TestClient, hospital_id, **overrides: object):
    return client.post(
        f"{PUBLIC_HOSPITALS}/{hospital_id}/family-requests", json=appeal_payload(**overrides)
    )


# ---------------------------------------------------------------------------------------
# Finding a hospital
# ---------------------------------------------------------------------------------------


def test_only_verified_hospitals_are_listed_without_signing_in(
    client: TestClient, db_session: Session
) -> None:
    _hospital(db_session, name="Verified Hospital")
    _hospital(
        db_session,
        email="staff2@example.com",
        name="Pending Clinic",
        status=VerificationStatus.PENDING,
    )

    names = [item["name"] for item in client.get(PUBLIC_HOSPITALS).json()]

    assert names == ["Verified Hospital"]


def test_the_hospital_with_the_postcode_given_comes_first_then_its_rings(
    client: TestClient, db_session: Session
) -> None:
    rows = [
        ("staff1@example.com", "Elsewhere", "LA-02-A01-KP-01"),
        ("staff2@example.com", "Same LGA", "FC-01-B02-MM-01"),
        ("staff3@example.com", "Exact", "FC-01-A01-KP-27"),
        ("staff4@example.com", "Same area", "FC-01-A01-KP-05"),
    ]
    for email, name, postcode in rows:
        _, hospital = _hospital(db_session, email=email, name=name)
        hospital.postcode = postcode
        db_session.add(hospital)
    db_session.commit()

    body = client.get(PUBLIC_HOSPITALS, params={"postcode": "fc01a01kp27"}).json()

    assert [item["name"] for item in body] == ["Exact", "Same area", "Same LGA", "Elsewhere"]
    assert body[1]["postcode_ring"] == "area"
    assert body[3]["postcode_ring"] is None


def test_a_position_ranks_hospitals_by_distance(client: TestClient, db_session: Session) -> None:
    _hospital(db_session, name="Far", latitude=9.07, longitude=7.39)
    _hospital(db_session, email="staff2@example.com", name="Near")

    body = client.get(PUBLIC_HOSPITALS, params={"latitude": 6.52, "longitude": 3.38}).json()

    assert [item["name"] for item in body] == ["Near", "Far"]
    assert body[0]["distance_km"] < body[1]["distance_km"]


def test_a_postcode_of_the_wrong_shape_is_refused(client: TestClient) -> None:
    assert client.get(PUBLIC_HOSPITALS, params={"postcode": "Wuse 2"}).status_code == 422


# ---------------------------------------------------------------------------------------
# Sending an appeal
# ---------------------------------------------------------------------------------------


def test_a_family_can_ask_a_verified_hospital_without_an_account(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)

    response = _send(client, hospital.id)

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"
    assert response.json()["hospital_name"] == hospital.name


def test_an_appeal_alerts_nobody_and_raises_no_request(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)

    _send(client, hospital.id)

    assert db_session.exec(select(BloodRequest)).all() == []


def test_the_family_must_confirm_the_patient_is_admitted(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)

    assert _send(client, hospital.id, patient_is_admitted=False).status_code == 422


def test_an_unverified_hospital_cannot_receive_appeals(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session, status=VerificationStatus.PENDING)

    assert _send(client, hospital.id).status_code == 404


def test_one_phone_can_have_only_a_few_appeals_waiting(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    for _ in range(MAX_PENDING_PER_PHONE):
        assert _send(client, hospital.id).status_code == 201

    assert _send(client, hospital.id).status_code == 409


def test_sending_is_rate_limited(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    statuses = [_send(client, hospital.id).status_code for _ in range(6)]

    assert statuses[-1] == 429


def test_the_family_can_follow_the_appeal_without_seeing_anything_personal(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    appeal_id = _send(client, hospital.id).json()["id"]

    body = client.get(f"{API}/public/family-requests/{appeal_id}").json()

    assert body["status"] == "pending"
    assert body["hospital_name"] == hospital.name
    assert body["units_pledged"] is None
    assert "requester_phone" not in body
    assert "requester_name" not in body


# ---------------------------------------------------------------------------------------
# The hospital answering
# ---------------------------------------------------------------------------------------


def test_staff_see_the_family_s_details_to_call_back(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    _send(client, hospital.id)
    sign_in(client, "staff1@example.com")

    [item] = client.get(STAFF).json()

    assert item["requester_phone"] == "+2348031112222"
    assert item["ward_reference"] == "Maternity ward, bed 4"
    assert item["component_name"]


def test_staff_never_see_another_hospital_s_appeals(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    _hospital(db_session, email="staff2@example.com", name="Other")
    _send(client, hospital.id)
    sign_in(client, "staff2@example.com")

    assert client.get(STAFF).json() == []


def test_approving_raises_a_blood_request_from_the_appeal(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    appeal_id = _send(client, hospital.id).json()["id"]
    sign_in(client, "staff1@example.com")

    response = client.post(f"{STAFF}/{appeal_id}/approve", json=approve_payload(units_needed=3))

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "approved"
    request = db_session.exec(select(BloodRequest)).one()
    assert request.status == RequestStatus.OPEN
    assert request.units_needed == 3
    assert request.recipient_group.value == "O+"
    assert "Maternity ward, bed 4" in (request.notes or "")
    assert str(request.id) == response.json()["blood_request_id"]
    assert db_session.exec(
        select(AuditLog).where(AuditLog.action == "family_request.approved")
    ).one()


def test_after_approval_the_family_sees_the_request_progress(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    appeal_id = _send(client, hospital.id).json()["id"]
    sign_in(client, "staff1@example.com")
    client.post(f"{STAFF}/{appeal_id}/approve", json=approve_payload())
    client.cookies.clear()

    body = client.get(f"{API}/public/family-requests/{appeal_id}").json()

    assert body["status"] == "approved"
    assert body["request_status"] == "open"
    assert body["units_pledged"] == 0


def test_declining_records_the_reason_for_the_family(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    appeal_id = _send(client, hospital.id).json()["id"]
    sign_in(client, "staff1@example.com")

    response = client.post(
        f"{STAFF}/{appeal_id}/decline", json={"reason": "No patient by that name on the ward"}
    )

    assert response.status_code == 200
    client.cookies.clear()
    body = client.get(f"{API}/public/family-requests/{appeal_id}").json()
    assert body["status"] == "declined"
    assert body["decline_reason"] == "No patient by that name on the ward"
    assert db_session.exec(select(BloodRequest)).all() == []


def test_an_appeal_can_only_be_decided_once(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    appeal_id = _send(client, hospital.id).json()["id"]
    sign_in(client, "staff1@example.com")
    client.post(f"{STAFF}/{appeal_id}/approve", json=approve_payload())

    again = client.post(f"{STAFF}/{appeal_id}/approve", json=approve_payload())
    decline = client.post(f"{STAFF}/{appeal_id}/decline", json={"reason": "Changed our mind"})

    assert again.status_code == 409
    assert decline.status_code == 409
    assert len(db_session.exec(select(BloodRequest)).all()) == 1


def test_a_deadline_in_the_past_is_refused_and_the_appeal_stays_waiting(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    appeal_id = _send(client, hospital.id).json()["id"]
    sign_in(client, "staff1@example.com")
    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()

    response = client.post(f"{STAFF}/{appeal_id}/approve", json=approve_payload(deadline=past))

    assert response.status_code == 422
    db_session.expire_all()
    appeal = db_session.exec(select(FamilyRequest)).one()
    assert appeal.status == FamilyRequestStatus.PENDING


def test_staff_of_another_hospital_cannot_decide_an_appeal(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital = _hospital(db_session)
    _hospital(db_session, email="staff2@example.com", name="Other")
    appeal_id = _send(client, hospital.id).json()["id"]
    sign_in(client, "staff2@example.com")

    assert client.post(f"{STAFF}/{appeal_id}/approve", json=approve_payload()).status_code == 404


def test_donors_cannot_use_the_staff_routes(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    assert client.get(STAFF).status_code == 403
