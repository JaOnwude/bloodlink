"""Tests of donor coverage by postcode ring, against a real database."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.enums import BloodGroup
from tests.helpers import API, make_donor_record, make_staff_with_hospital, register_user, sign_in

COVERAGE = f"{API}/stats/coverage"


def _donor(db_session: Session, email: str, area: str | None, **fields: object) -> None:
    donor = make_donor_record(db_session, email=email, **fields)
    donor.postcode_area = area
    db_session.add(donor)
    db_session.commit()


def _signed_in_hospital(client: TestClient, db_session: Session, postcode: str | None):
    _, hospital = make_staff_with_hospital(db_session)
    hospital.postcode = postcode
    db_session.add(hospital)
    db_session.commit()
    sign_in(client, "staff1@example.com")
    return hospital


def test_donors_are_counted_in_every_ring_that_contains_them(
    client: TestClient, db_session: Session
) -> None:
    _signed_in_hospital(client, db_session, "LA-01-A01-KP-27")
    _donor(db_session, "area@example.com", "LA-01-A01-KP", blood_group=BloodGroup.O_NEGATIVE)
    _donor(db_session, "district@example.com", "LA-01-A01-MM", blood_group=BloodGroup.O_POSITIVE)
    _donor(db_session, "lga@example.com", "LA-01-B02-KP", blood_group=BloodGroup.O_POSITIVE)
    _donor(db_session, "state@example.com", "LA-02-A01-KP", blood_group=BloodGroup.A_POSITIVE)
    _donor(db_session, "elsewhere@example.com", "FC-01-A01-KP")

    body = client.get(COVERAGE).json()

    rings = {ring["ring"]: ring for ring in body["rings"]}
    assert [ring["ring"] for ring in body["rings"]] == ["area", "district", "lga", "state"]
    assert rings["area"]["prefix"] == "LA-01-A01-KP"
    assert rings["lga"]["prefix"] == "LA-01"
    assert [rings[name]["total"] for name in ("area", "district", "lga", "state")] == [1, 2, 3, 4]
    assert rings["lga"]["by_group"] == {"O-": 1, "O+": 2}


def test_donors_who_cannot_be_reached_are_not_counted(
    client: TestClient, db_session: Session
) -> None:
    _signed_in_hospital(client, db_session, "LA-01-A01-KP-27")
    _donor(db_session, "paused@example.com", "LA-01-A01-KP", is_available=False)
    _donor(db_session, "private@example.com", "LA-01-A01-KP", consent=False)
    _donor(db_session, "inactive@example.com", "LA-01-A01-KP", is_active=False)

    body = client.get(COVERAGE).json()

    assert all(ring["total"] == 0 for ring in body["rings"])


def test_nearby_donors_without_a_postcode_are_counted_apart(
    client: TestClient, db_session: Session
) -> None:
    _signed_in_hospital(client, db_session, "LA-01-A01-KP-27")
    _donor(db_session, "near@example.com", None)
    _donor(db_session, "far@example.com", None, latitude=9.07, longitude=7.39)

    body = client.get(COVERAGE).json()

    assert body["without_postcode_nearby"] == 1


def test_a_hospital_without_a_postcode_has_no_rings(
    client: TestClient, db_session: Session
) -> None:
    _signed_in_hospital(client, db_session, None)

    body = client.get(COVERAGE).json()

    assert body["postcode"] is None
    assert body["rings"] == []


def test_coverage_is_for_hospital_staff_only(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    assert client.get(COVERAGE).status_code == 403
