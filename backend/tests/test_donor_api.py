"""Tests of the donor profile and eligibility endpoints against a real database."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Donor
from tests.helpers import API, donor_payload, register_user, sign_in

PROFILE = f"{API}/donors/me"


def today():
    return datetime.now(UTC).date()


# ---------------------------------------------------------------------------------------
# Creating, reading and updating the profile
# ---------------------------------------------------------------------------------------


def test_first_save_creates_the_profile_and_later_saves_update_it(
    client: TestClient, db_session: Session
) -> None:
    register_user(client, email="donor1@example.com")

    created = client.put(PROFILE, json=donor_payload())
    updated = client.put(PROFILE, json=donor_payload(weight_kg=80, city="Abuja"))

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["id"] == created.json()["id"]
    assert updated.json()["city"] == "Abuja"
    assert len(db_session.exec(select(Donor)).all()) == 1


def test_the_profile_can_be_read_back(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")
    client.put(PROFILE, json=donor_payload())

    body = client.get(PROFILE).json()

    assert body["blood_group"] == "O-"
    assert body["city"] == "Port Harcourt"
    assert body["consent_to_contact"] is True


def test_reading_before_creating_a_profile_returns_404(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    assert client.get(PROFILE).status_code == 404


def test_consent_defaults_to_not_given(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")
    body = donor_payload()
    del body["consent_to_contact"]

    assert client.put(PROFILE, json=body).json()["consent_to_contact"] is False


def test_two_donors_keep_separate_profiles(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")
    client.put(PROFILE, json=donor_payload(city="Port Harcourt"))
    register_user(client, email="donor2@example.com")
    client.put(PROFILE, json=donor_payload(city="Enugu"))

    assert client.get(PROFILE).json()["city"] == "Enugu"
    sign_in(client, "donor1@example.com")
    assert client.get(PROFILE).json()["city"] == "Port Harcourt"


# ---------------------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------------------


def test_anonymous_callers_are_refused(client: TestClient) -> None:
    assert client.get(PROFILE).status_code == 401
    assert client.put(PROFILE, json=donor_payload()).status_code == 401


def test_hospital_staff_cannot_use_donor_endpoints(client: TestClient) -> None:
    register_user(client, email="staff1@example.com", role="hospital_staff")

    assert client.get(PROFILE).status_code == 403
    assert client.put(PROFILE, json=donor_payload()).status_code == 403
    assert client.get(f"{PROFILE}/eligibility").status_code == 403


# ---------------------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------------------


def test_out_of_range_coordinates_are_rejected(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    assert client.put(PROFILE, json=donor_payload(latitude=91)).status_code == 422
    assert client.put(PROFILE, json=donor_payload(longitude=-181)).status_code == 422


def test_a_weight_of_zero_is_rejected(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    assert client.put(PROFILE, json=donor_payload(weight_kg=0)).status_code == 422


def test_a_birth_date_in_the_future_is_rejected(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    assert client.put(PROFILE, json=donor_payload(date_of_birth="2999-01-01")).status_code == 422


def test_a_last_donation_in_the_future_is_rejected(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")
    future = str(today() + timedelta(days=30))

    assert client.put(PROFILE, json=donor_payload(last_donation_date=future)).status_code == 422


def test_a_last_donation_before_birth_is_rejected(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    response = client.put(PROFILE, json=donor_payload(last_donation_date="1990-01-01"))

    assert response.status_code == 422


def test_a_blank_city_is_rejected(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    assert client.put(PROFILE, json=donor_payload(city="   ")).status_code == 422


# ---------------------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------------------


def test_alerts_can_be_paused_and_resumed(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")
    client.put(PROFILE, json=donor_payload())

    paused = client.patch(f"{PROFILE}/availability", json={"is_available": False})
    assert paused.status_code == 200
    assert client.get(PROFILE).json()["is_available"] is False

    client.patch(f"{PROFILE}/availability", json={"is_available": True})
    assert client.get(PROFILE).json()["is_available"] is True


def test_availability_needs_a_profile(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    response = client.patch(f"{PROFILE}/availability", json={"is_available": False})

    assert response.status_code == 404


# ---------------------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------------------


def test_a_donor_who_has_never_donated_is_eligible(
    client: TestClient, reference_data: None
) -> None:
    register_user(client, email="donor1@example.com")
    client.put(PROFILE, json=donor_payload())

    body = client.get(f"{PROFILE}/eligibility").json()

    assert body["eligible_for_any"] is True
    assert body["blockers"] == []
    assert "whole_blood" in {item["component_code"] for item in body["components"]}


def test_a_donor_who_gave_yesterday_must_wait(client: TestClient, reference_data: None) -> None:
    register_user(client, email="donor1@example.com")
    yesterday = str(today() - timedelta(days=1))
    client.put(PROFILE, json=donor_payload(last_donation_date=yesterday))

    body = client.get(f"{PROFILE}/eligibility").json()

    assert body["eligible_for_any"] is False
    for item in body["components"]:
        assert item["eligible"] is False
        assert item["next_eligible_date"] > str(today())


def test_an_underage_donor_sees_the_reason(client: TestClient, reference_data: None) -> None:
    register_user(client, email="donor1@example.com")
    ten_years_ago = str(today() - timedelta(days=365 * 10))
    client.put(PROFILE, json=donor_payload(date_of_birth=ten_years_ago))

    body = client.get(f"{PROFILE}/eligibility").json()

    assert body["eligible_for_any"] is False
    assert body["blockers"]


def test_eligibility_needs_a_profile(client: TestClient, reference_data: None) -> None:
    register_user(client, email="donor1@example.com")

    assert client.get(f"{PROFILE}/eligibility").status_code == 404
