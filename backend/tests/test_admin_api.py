"""Tests of the administrator's hospital review endpoints, against a real database."""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import AuditLog, Hospital
from app.models.enums import VerificationStatus
from tests.helpers import API, hospital_payload, make_admin, register_user, sign_in

ADMIN = f"{API}/admin/hospitals"


def pending_hospital(client: TestClient, email: str, name: str = "Rivers General") -> str:
    """Register a staff member and their hospital. Leaves the client signed in as that staff."""
    register_user(client, email=email, role="hospital_staff")
    response = client.post(f"{API}/hospitals", json=hospital_payload(name=name))
    assert response.status_code == 201, response.text
    return response.json()["id"]


def sign_in_as_admin(client: TestClient, db_session: Session) -> None:
    make_admin(db_session)
    sign_in(client, "admin@example.com")


# ---------------------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------------------


def test_anonymous_callers_are_refused(client: TestClient) -> None:
    assert client.get(ADMIN).status_code == 401


def test_staff_and_donors_cannot_use_admin_endpoints(client: TestClient) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    assert client.get(ADMIN).status_code == 403
    assert client.post(f"{ADMIN}/{hospital_id}/verify").status_code == 403

    register_user(client, email="donor1@example.com", role="donor")
    assert client.get(ADMIN).status_code == 403
    rejection = client.post(f"{ADMIN}/{hospital_id}/reject", json={"reason": "No reason"})
    assert rejection.status_code == 403


# ---------------------------------------------------------------------------------------
# The review queue
# ---------------------------------------------------------------------------------------


def test_the_queue_lists_pending_hospitals_with_their_staff(
    client: TestClient, db_session: Session
) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    sign_in_as_admin(client, db_session)

    page = client.get(ADMIN).json()

    assert page["total"] == 1
    item = page["items"][0]
    assert item["id"] == hospital_id
    assert item["staff"][0]["email"] == "staff1@example.com"


def test_the_queue_can_be_filtered_by_status(client: TestClient, db_session: Session) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    sign_in_as_admin(client, db_session)
    client.post(f"{ADMIN}/{hospital_id}/verify")

    assert client.get(ADMIN).json()["total"] == 0
    verified = client.get(ADMIN, params={"status": "verified"}).json()
    assert verified["total"] == 1


def test_the_queue_is_paginated(client: TestClient, db_session: Session) -> None:
    for number in range(3):
        pending_hospital(client, f"staff{number}@example.com", name=f"Hospital {number}")
    sign_in_as_admin(client, db_session)

    first = client.get(ADMIN, params={"limit": 2}).json()
    rest = client.get(ADMIN, params={"limit": 2, "offset": 2}).json()

    assert first["total"] == 3
    assert len(first["items"]) == 2
    assert len(rest["items"]) == 1


def test_one_hospital_can_be_read_with_its_staff(
    client: TestClient, db_session: Session
) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    sign_in_as_admin(client, db_session)

    response = client.get(f"{ADMIN}/{hospital_id}")

    assert response.status_code == 200
    assert response.json()["staff"][0]["full_name"] == "Test Person"


def test_an_unknown_hospital_returns_404(client: TestClient, db_session: Session) -> None:
    sign_in_as_admin(client, db_session)

    assert client.get(f"{ADMIN}/{uuid4()}").status_code == 404
    assert client.post(f"{ADMIN}/{uuid4()}/verify").status_code == 404


def test_a_malformed_id_is_a_validation_error(client: TestClient, db_session: Session) -> None:
    sign_in_as_admin(client, db_session)

    assert client.get(f"{ADMIN}/not-a-uuid").status_code == 422


# ---------------------------------------------------------------------------------------
# Verifying
# ---------------------------------------------------------------------------------------


def test_verifying_marks_the_hospital_and_records_who_did_it(
    client: TestClient, db_session: Session
) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    admin = make_admin(db_session)
    sign_in(client, "admin@example.com")

    response = client.post(f"{ADMIN}/{hospital_id}/verify")

    assert response.status_code == 200
    assert response.json()["verification_status"] == "verified"
    assert response.json()["verified_at"] is not None
    entry = db_session.exec(select(AuditLog).where(AuditLog.action == "hospital.verified")).one()
    assert entry.actor_user_id == admin.id
    assert entry.before == {"verification_status": "pending"}
    assert entry.after == {"verification_status": "verified"}
    assert entry.ip_address == "testclient"


def test_verifying_twice_conflicts(client: TestClient, db_session: Session) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    sign_in_as_admin(client, db_session)
    client.post(f"{ADMIN}/{hospital_id}/verify")

    assert client.post(f"{ADMIN}/{hospital_id}/verify").status_code == 409


def test_a_verified_hospital_shows_as_verified_to_its_staff(
    client: TestClient, db_session: Session
) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    sign_in_as_admin(client, db_session)
    client.post(f"{ADMIN}/{hospital_id}/verify")
    sign_in(client, "staff1@example.com")

    assert client.get(f"{API}/hospitals/me").json()["verification_status"] == "verified"


# ---------------------------------------------------------------------------------------
# Rejecting and revoking
# ---------------------------------------------------------------------------------------


def test_rejecting_needs_a_real_reason(client: TestClient, db_session: Session) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    sign_in_as_admin(client, db_session)

    assert client.post(f"{ADMIN}/{hospital_id}/reject", json={"reason": "no"}).status_code == 422
    assert client.post(f"{ADMIN}/{hospital_id}/reject", json={}).status_code == 422


def test_rejecting_records_the_reason_and_shows_it_to_the_staff(
    client: TestClient, db_session: Session
) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    sign_in_as_admin(client, db_session)

    response = client.post(
        f"{ADMIN}/{hospital_id}/reject", json={"reason": "Registration number could not be found"}
    )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "rejected"
    entry = db_session.exec(select(AuditLog).where(AuditLog.action == "hospital.rejected")).one()
    assert entry.after["rejection_reason"] == "Registration number could not be found"
    sign_in(client, "staff1@example.com")
    mine = client.get(f"{API}/hospitals/me").json()
    assert mine["rejection_reason"] == "Registration number could not be found"


def test_rejecting_twice_conflicts(client: TestClient, db_session: Session) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    sign_in_as_admin(client, db_session)
    client.post(f"{ADMIN}/{hospital_id}/reject", json={"reason": "Not a real facility"})

    again = client.post(f"{ADMIN}/{hospital_id}/reject", json={"reason": "Still not real"})

    assert again.status_code == 409


def test_verification_can_be_revoked(client: TestClient, db_session: Session) -> None:
    hospital_id = pending_hospital(client, "staff1@example.com")
    sign_in_as_admin(client, db_session)
    client.post(f"{ADMIN}/{hospital_id}/verify")

    response = client.post(
        f"{ADMIN}/{hospital_id}/reject", json={"reason": "Licence has been withdrawn"}
    )

    assert response.status_code == 200
    assert response.json()["verification_status"] == "rejected"
    assert response.json()["verified_at"] is None
    db_session.expire_all()
    hospital = db_session.exec(select(Hospital)).one()
    assert hospital.verification_status is VerificationStatus.REJECTED
