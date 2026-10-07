"""Tests of hospital registration by staff, against a real database."""

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.deps import get_verified_hospital
from app.models import AuditLog, Hospital, User
from app.models.enums import UserRole, VerificationStatus
from app.services.auth import create_user
from tests.helpers import API, PASSWORD, hospital_payload, make_admin, register_user, sign_in

HOSPITALS = f"{API}/hospitals"


def staff_with_hospital(client: TestClient, email: str, **overrides: object) -> dict:
    register_user(client, email=email, role="hospital_staff")
    response = client.post(HOSPITALS, json=hospital_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------------------
# Registering
# ---------------------------------------------------------------------------------------


def test_staff_can_register_a_hospital_which_starts_pending(client: TestClient) -> None:
    register_user(client, email="staff1@example.com", role="hospital_staff")

    response = client.post(HOSPITALS, json=hospital_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["verification_status"] == "pending"
    assert body["verified_at"] is None
    assert body["contact_phone"] == "+2348031234567"


def test_the_staff_member_is_linked_to_the_new_hospital(client: TestClient) -> None:
    created = staff_with_hospital(client, "staff1@example.com")

    mine = client.get(f"{HOSPITALS}/me")

    assert mine.status_code == 200
    assert mine.json()["id"] == created["id"]
    assert client.get(f"{API}/auth/me").json()["hospital_id"] == created["id"]


def test_registration_is_recorded_in_the_audit_log(
    client: TestClient, db_session: Session
) -> None:
    created = staff_with_hospital(client, "staff1@example.com")

    entry = db_session.exec(
        select(AuditLog).where(AuditLog.action == "hospital.registered")
    ).one()

    assert str(entry.entity_id) == created["id"]
    assert entry.actor_user_id is not None
    assert entry.after["verification_status"] == "pending"
    assert entry.ip_address == "testclient"


def test_a_second_registration_by_the_same_staff_member_conflicts(client: TestClient) -> None:
    staff_with_hospital(client, "staff1@example.com")

    again = client.post(HOSPITALS, json=hospital_payload(name="Another Hospital"))

    assert again.status_code == 409


def test_reading_before_registering_returns_404(client: TestClient) -> None:
    register_user(client, email="staff1@example.com", role="hospital_staff")

    assert client.get(f"{HOSPITALS}/me").status_code == 404


def test_donors_cannot_register_hospitals(client: TestClient) -> None:
    register_user(client, email="donor1@example.com", role="donor")

    assert client.post(HOSPITALS, json=hospital_payload()).status_code == 403


def test_anonymous_callers_are_refused(client: TestClient) -> None:
    assert client.post(HOSPITALS, json=hospital_payload()).status_code == 401
    assert client.get(f"{HOSPITALS}/me").status_code == 401


def test_invalid_details_are_rejected(client: TestClient) -> None:
    register_user(client, email="staff1@example.com", role="hospital_staff")

    assert client.post(HOSPITALS, json=hospital_payload(latitude=95)).status_code == 422
    assert client.post(HOSPITALS, json=hospital_payload(contact_phone="")).status_code == 422
    assert client.post(HOSPITALS, json=hospital_payload(name=" ")).status_code == 422


def test_a_blank_registration_number_is_stored_as_nothing(client: TestClient) -> None:
    register_user(client, email="staff1@example.com", role="hospital_staff")

    response = client.post(HOSPITALS, json=hospital_payload(registration_number="  "))

    assert response.json()["registration_number"] is None


def test_each_staff_member_sees_only_their_own_hospital(client: TestClient) -> None:
    staff_with_hospital(client, "staff1@example.com", name="First Hospital")
    staff_with_hospital(client, "staff2@example.com", name="Second Hospital")

    assert client.get(f"{HOSPITALS}/me").json()["name"] == "Second Hospital"
    sign_in(client, "staff1@example.com")
    assert client.get(f"{HOSPITALS}/me").json()["name"] == "First Hospital"


# ---------------------------------------------------------------------------------------
# Editing
# ---------------------------------------------------------------------------------------


def test_details_can_be_corrected_while_pending(client: TestClient, db_session: Session) -> None:
    staff_with_hospital(client, "staff1@example.com")

    response = client.put(f"{HOSPITALS}/me", json=hospital_payload(address="45 New Road, GRA"))

    assert response.status_code == 200
    assert response.json()["address"] == "45 New Road, GRA"
    assert response.json()["verification_status"] == "pending"
    actions = {entry.action for entry in db_session.exec(select(AuditLog)).all()}
    assert "hospital.updated" in actions


def test_a_verified_hospital_cannot_be_edited_by_its_staff(
    client: TestClient, db_session: Session
) -> None:
    created = staff_with_hospital(client, "staff1@example.com")
    make_admin(db_session)
    sign_in(client, "admin@example.com")
    assert client.post(f"{API}/admin/hospitals/{created['id']}/verify").status_code == 200
    sign_in(client, "staff1@example.com")

    response = client.put(f"{HOSPITALS}/me", json=hospital_payload(address="Somewhere else"))

    assert response.status_code == 409


def test_editing_a_rejected_hospital_sends_it_back_for_review(
    client: TestClient, db_session: Session
) -> None:
    created = staff_with_hospital(client, "staff1@example.com")
    make_admin(db_session)
    sign_in(client, "admin@example.com")
    client.post(
        f"{API}/admin/hospitals/{created['id']}/reject", json={"reason": "Licence number missing"}
    )
    sign_in(client, "staff1@example.com")
    assert client.get(f"{HOSPITALS}/me").json()["rejection_reason"] == "Licence number missing"

    response = client.put(f"{HOSPITALS}/me", json=hospital_payload(registration_number="RV-999"))

    assert response.status_code == 200
    assert response.json()["verification_status"] == "pending"
    assert response.json()["rejection_reason"] is None
    actions = {entry.action for entry in db_session.exec(select(AuditLog)).all()}
    assert "hospital.resubmitted" in actions


def test_editing_without_a_hospital_returns_404(client: TestClient) -> None:
    register_user(client, email="staff1@example.com", role="hospital_staff")

    assert client.put(f"{HOSPITALS}/me", json=hospital_payload()).status_code == 404


# ---------------------------------------------------------------------------------------
# The verified-hospital gate used by features that act for a hospital
# ---------------------------------------------------------------------------------------


def make_staff(db_session: Session, hospital: Hospital | None) -> User:
    staff = create_user(
        db_session,
        email="gate-staff@example.com",
        password=PASSWORD,
        full_name="Gate Staff",
        role=UserRole.HOSPITAL_STAFF,
    )
    if hospital is not None:
        db_session.add(hospital)
        db_session.commit()
        staff.hospital_id = hospital.id
        db_session.add(staff)
        db_session.commit()
    return staff


def make_hospital(status: VerificationStatus) -> Hospital:
    return Hospital(
        name="Gate Hospital",
        address="1 Gate Road",
        city="Lagos",
        state="Lagos",
        latitude=6.5,
        longitude=3.4,
        contact_phone="+2348000000000",
        verification_status=status,
    )


def test_the_gate_refuses_staff_without_a_hospital(db_session: Session) -> None:
    staff = make_staff(db_session, None)

    try:
        get_verified_hospital(staff, db_session)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Staff without a hospital must be refused.")


def test_the_gate_refuses_a_pending_hospital(db_session: Session) -> None:
    staff = make_staff(db_session, make_hospital(VerificationStatus.PENDING))

    try:
        get_verified_hospital(staff, db_session)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("A pending hospital must be refused.")


def test_the_gate_lets_a_verified_hospital_through(db_session: Session) -> None:
    hospital = make_hospital(VerificationStatus.VERIFIED)
    staff = make_staff(db_session, hospital)

    assert get_verified_hospital(staff, db_session).id == hospital.id
