"""Tests of postcode checks, searches and postcodes on profiles, against a real database.

Every test runs on the offline mock (see ``never_call_nipost`` in ``conftest.py``), whose
known postcodes are the five in NIPOST's sandbox.
"""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.routes.postcodes import postcode_client
from app.core.config import get_settings
from app.main import app
from app.models import Donor, Hospital
from app.services.postcode import PostcodeServiceError
from tests.helpers import (
    API,
    donor_payload,
    hospital_payload,
    make_admin,
    make_staff_with_hospital,
    register_user,
    sign_in,
)

CHECK = f"{API}/postcodes/check"
AT = f"{API}/postcodes/at"
PROFILE = f"{API}/donors/me"
HOSPITALS = f"{API}/hospitals"

SANDBOX_POSTCODE = "FC-01-A01-KP-27"
UNASSIGNED_POSTCODE = "LA-01-A01-AA-01"


class _Unavailable:
    """A postcode client whose every call fails, as when NIPOST is down."""

    name = "test"

    def lookup(self, postcode: str, level: int):
        raise PostcodeServiceError("The postcode service could not be reached.")

    def reverse(self, latitude: float, longitude: float, max_distance_m: int):
        raise PostcodeServiceError("The postcode service could not be reached.")

    def lga_names(self, state: str):
        raise PostcodeServiceError("The postcode service could not be reached.")


# ---------------------------------------------------------------------------------------
# Checking and finding postcodes
# ---------------------------------------------------------------------------------------


def test_checking_needs_a_signed_in_account(client: TestClient) -> None:
    assert client.get(CHECK, params={"code": SANDBOX_POSTCODE}).status_code == 401
    assert client.get(AT, params={"latitude": 9.07, "longitude": 7.39}).status_code == 401


def test_an_assigned_postcode_is_valid_with_its_lga(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    body = client.get(CHECK, params={"code": "fc 01 a01 kp 27"}).json()

    assert body["postcode"] == SANDBOX_POSTCODE
    assert body["valid"] is True
    assert body["area_code"] == "FC-01-A01-KP"
    assert (body["state_code"], body["lga_code"]) == ("FC", "01")
    assert body["lga_name"]
    assert body["source"] == "mock"


def test_an_unassigned_postcode_is_not_valid(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    body = client.get(CHECK, params={"code": UNASSIGNED_POSTCODE}).json()

    assert body["valid"] is False
    assert body["lga_name"] is None


def test_text_not_shaped_like_a_postcode_is_rejected_without_asking_nipost(
    client: TestClient,
) -> None:
    register_user(client, email="donor1@example.com")
    app.dependency_overrides[postcode_client] = _Unavailable

    assert client.get(CHECK, params={"code": "Wuse 2, Abuja"}).status_code == 422


def test_the_postcode_at_a_sample_building_is_found(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    body = client.get(AT, params={"latitude": 9.0765, "longitude": 7.3986}).json()

    assert body["found"] is True
    assert body["postcode"] == SANDBOX_POSTCODE


def test_nothing_is_found_far_from_any_building(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    body = client.get(AT, params={"latitude": 6.5244, "longitude": 3.3792}).json()

    assert body == {"found": False, "postcode": None, "distance_m": None, "source": "mock"}


def test_the_search_distance_cannot_exceed_nipost_s_limit(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    response = client.get(AT, params={"latitude": 9.07, "longitude": 7.39, "max_distance_m": 251})

    assert response.status_code == 422


def test_nipost_being_down_is_reported_as_unavailable(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")
    app.dependency_overrides[postcode_client] = _Unavailable

    assert client.get(CHECK, params={"code": SANDBOX_POSTCODE}).status_code == 503
    assert client.get(AT, params={"latitude": 9.07, "longitude": 7.39}).status_code == 503


# ---------------------------------------------------------------------------------------
# A donor's postcode: only the area is kept
# ---------------------------------------------------------------------------------------


def test_a_donor_s_postcode_is_cut_back_to_its_area(
    client: TestClient, db_session: Session
) -> None:
    register_user(client, email="donor1@example.com")

    response = client.put(PROFILE, json=donor_payload(postcode="fc01a01kp27"))

    assert response.status_code == 201, response.text
    assert response.json()["postcode_area"] == "FC-01-A01-KP"
    stored = db_session.exec(select(Donor)).one()
    assert stored.postcode_area == "FC-01-A01-KP"
    assert "27" not in stored.postcode_area.split("-")[-1]


def test_a_donor_postcode_nipost_has_not_assigned_is_refused_on_the_field(
    client: TestClient,
) -> None:
    register_user(client, email="donor1@example.com")

    response = client.put(PROFILE, json=donor_payload(postcode=UNASSIGNED_POSTCODE))

    assert response.status_code == 422
    [error] = response.json()["detail"]
    assert error["loc"] == ["body", "postcode"]


def test_leaving_the_postcode_out_keeps_the_saved_area(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")
    client.put(PROFILE, json=donor_payload(postcode=SANDBOX_POSTCODE))

    body = client.put(PROFILE, json=donor_payload(weight_kg=80)).json()

    assert body["postcode_area"] == "FC-01-A01-KP"


def test_sending_no_postcode_removes_the_saved_area(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")
    client.put(PROFILE, json=donor_payload(postcode=SANDBOX_POSTCODE))

    body = client.put(PROFILE, json=donor_payload(postcode=None)).json()

    assert body["postcode_area"] is None


def test_a_donor_can_still_save_without_a_postcode(client: TestClient) -> None:
    register_user(client, email="donor1@example.com")

    response = client.put(PROFILE, json=donor_payload())

    assert response.status_code == 201
    assert response.json()["postcode_area"] is None


# ---------------------------------------------------------------------------------------
# A hospital's postcode: the full building code is kept
# ---------------------------------------------------------------------------------------


def test_a_hospital_keeps_its_full_building_postcode(
    client: TestClient, db_session: Session
) -> None:
    register_user(client, email="staff1@example.com", role="hospital_staff")

    response = client.post(HOSPITALS, json=hospital_payload(postcode="FC 01 A01 KP 27"))

    assert response.status_code == 201, response.text
    assert response.json()["postcode"] == SANDBOX_POSTCODE
    assert db_session.exec(select(Hospital)).one().postcode == SANDBOX_POSTCODE


def test_a_hospital_postcode_nipost_has_not_assigned_is_refused(client: TestClient) -> None:
    register_user(client, email="staff1@example.com", role="hospital_staff")

    response = client.post(HOSPITALS, json=hospital_payload(postcode=UNASSIGNED_POSTCODE))

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "postcode"]


def test_a_hospital_postcode_of_the_wrong_shape_is_refused(client: TestClient) -> None:
    register_user(client, email="staff1@example.com", role="hospital_staff")

    response = client.post(HOSPITALS, json=hospital_payload(postcode="FC-01"))

    assert response.status_code == 422


# ---------------------------------------------------------------------------------------
# An administrator's look at a hospital's building
# ---------------------------------------------------------------------------------------


def _hospital_with_postcode(db_session: Session, postcode: str | None) -> Hospital:
    _, hospital = make_staff_with_hospital(db_session)
    hospital.postcode = postcode
    db_session.add(hospital)
    db_session.commit()
    return hospital


def test_an_administrator_sees_what_nipost_records_about_the_building(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "nipost_max_lookup_level", 3)
    hospital = _hospital_with_postcode(db_session, SANDBOX_POSTCODE)
    make_admin(db_session)
    sign_in(client, "admin@example.com")

    body = client.get(f"{API}/admin/hospitals/{hospital.id}/postcode-record").json()

    assert body["valid"] is True
    assert body["level"] == 3
    assert body["building_use_status"] == "public"
    assert body["lga_name"]


def test_at_level_1_the_record_says_only_that_the_postcode_is_assigned(
    client: TestClient, db_session: Session
) -> None:
    hospital = _hospital_with_postcode(db_session, SANDBOX_POSTCODE)
    make_admin(db_session)
    sign_in(client, "admin@example.com")

    body = client.get(f"{API}/admin/hospitals/{hospital.id}/postcode-record").json()

    assert body["valid"] is True
    assert body["level"] == 1
    assert body["house_address"] is None
    assert body["building_use_status"] is None


def test_a_hospital_without_a_postcode_has_no_record(
    client: TestClient, db_session: Session
) -> None:
    hospital = _hospital_with_postcode(db_session, None)
    make_admin(db_session)
    sign_in(client, "admin@example.com")

    assert client.get(f"{API}/admin/hospitals/{hospital.id}/postcode-record").status_code == 404


def test_only_administrators_see_the_record(client: TestClient, db_session: Session) -> None:
    hospital = _hospital_with_postcode(db_session, SANDBOX_POSTCODE)
    sign_in(client, "staff1@example.com")

    assert client.get(f"{API}/admin/hospitals/{hospital.id}/postcode-record").status_code == 403
