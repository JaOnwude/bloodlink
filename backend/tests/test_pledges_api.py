"""Tests of pledging, cancelling and recording outcomes, through the API.

These cover the second hard part of the project from the outside: a request is never
promised more units than it needs, a donor cannot pledge twice, and every change to the
units taken moves the request between open and fulfilled correctly. The simultaneous
case is covered in ``test_pledge_concurrency``.
"""

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import AuditLog, BloodRequest, Donation, Donor, Pledge
from app.models.enums import BloodGroup, PledgeStatus, RequestStatus
from tests.helpers import (
    API,
    make_request_record,
    make_signed_in_donor,
    make_staff_with_hospital,
    sign_in,
)


def pledge(client: TestClient, request_id) -> object:
    return client.post(f"{API}/requests/{request_id}/pledges")


def setup_request(db_session: Session, **overrides):
    """A verified Lagos hospital with one open O- whole blood request for two units."""
    staff, hospital = make_staff_with_hospital(db_session)
    request = make_request_record(db_session, hospital, staff, **overrides)
    return staff, hospital, request


def reload(db_session: Session, model, key):
    db_session.expire_all()
    return db_session.get(model, key)


# ---------------------------------------------------------------------------------------
# Pledging
# ---------------------------------------------------------------------------------------


def test_a_compatible_eligible_donor_can_pledge(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")

    response = pledge(client, request.id)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pledged"
    assert body["request_status"] == "open"
    assert body["units_remaining"] == 1
    entry = db_session.exec(select(AuditLog).where(AuditLog.action == "pledge.created")).one()
    assert entry.entity_id is not None


def test_sequential_pledges_stop_at_the_units_needed(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session, units_needed=2)

    statuses = []
    for number in range(3):
        make_signed_in_donor(client, email=f"donor{number}@example.com")
        statuses.append(pledge(client, request.id).status_code)

    assert statuses == [201, 201, 409]
    counted = db_session.exec(
        select(Pledge).where(Pledge.request_id == request.id, Pledge.status == "pledged")
    ).all()
    assert len(counted) == 2


def test_the_pledge_for_the_last_unit_fulfils_the_request(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session, units_needed=1)
    make_signed_in_donor(client, email="donor1@example.com")

    body = pledge(client, request.id).json()

    assert body["request_status"] == "fulfilled"
    assert body["units_remaining"] == 0
    saved = reload(db_session, BloodRequest, request.id)
    assert saved.status == RequestStatus.FULFILLED
    assert saved.fulfilled_at is not None
    assert db_session.exec(select(AuditLog).where(AuditLog.action == "request.fulfilled")).one()


def test_a_donor_cannot_pledge_twice_to_the_same_request(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session, units_needed=3)
    make_signed_in_donor(client, email="donor1@example.com")

    assert pledge(client, request.id).status_code == 201
    second = pledge(client, request.id)

    assert second.status_code == 409
    assert "already pledged" in second.json()["detail"]


def test_an_incompatible_donor_is_refused(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session, recipient_group=BloodGroup.O_NEGATIVE)
    make_signed_in_donor(client, email="donor1@example.com", blood_group="A+")

    response = pledge(client, request.id)

    assert response.status_code == 403
    assert "cannot be given" in response.json()["detail"]


def test_a_donor_inside_the_waiting_period_is_refused(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session)
    recent = (datetime.now(UTC).date() - timedelta(days=10)).isoformat()
    make_signed_in_donor(client, email="donor1@example.com", last_donation_date=recent)

    response = pledge(client, request.id)

    assert response.status_code == 403
    assert "again until" in response.json()["detail"]


def test_a_closed_request_takes_no_pledges(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session, status=RequestStatus.CLOSED)
    make_signed_in_donor(client, email="donor1@example.com")

    assert pledge(client, request.id).status_code == 409


def test_an_overdue_request_is_expired_instead_of_pledged(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session, deadline=datetime.now(UTC) - timedelta(minutes=1))
    make_signed_in_donor(client, email="donor1@example.com")

    response = pledge(client, request.id)

    assert response.status_code == 409
    assert reload(db_session, BloodRequest, request.id).status == RequestStatus.EXPIRED


def test_a_donor_holds_only_one_active_pledge(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital, first = setup_request(db_session)
    second = make_request_record(db_session, hospital, staff)
    make_signed_in_donor(client, email="donor1@example.com")

    assert pledge(client, first.id).status_code == 201
    response = pledge(client, second.id)

    assert response.status_code == 409
    assert "another request" in response.json()["detail"]


def test_an_unknown_request_is_not_found(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    make_signed_in_donor(client, email="donor1@example.com")

    assert pledge(client, "00000000-0000-0000-0000-000000000000").status_code == 404


def test_staff_cannot_pledge(client: TestClient, db_session: Session, reference_data: None) -> None:
    staff, _, request = setup_request(db_session)
    sign_in(client, staff.email)

    assert pledge(client, request.id).status_code == 403


# ---------------------------------------------------------------------------------------
# Cancelling
# ---------------------------------------------------------------------------------------


def test_cancelling_frees_the_unit_and_reopens_a_fulfilled_request(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session, units_needed=1)
    make_signed_in_donor(client, email="donor1@example.com")
    pledge_id = pledge(client, request.id).json()["id"]

    response = client.delete(f"{API}/pledges/{pledge_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["request_status"] == "open"
    assert body["units_remaining"] == 1
    assert reload(db_session, BloodRequest, request.id).fulfilled_at is None


def test_a_donor_who_cancelled_can_pledge_again(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")
    first_id = pledge(client, request.id).json()["id"]
    client.delete(f"{API}/pledges/{first_id}")

    again = pledge(client, request.id)

    assert again.status_code == 201
    # The same row is reused, as the unique constraint on (request, donor) requires.
    assert again.json()["id"] == first_id


def test_a_donor_cannot_cancel_someone_elses_pledge(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")
    pledge_id = pledge(client, request.id).json()["id"]

    make_signed_in_donor(client, email="donor2@example.com")

    assert client.delete(f"{API}/pledges/{pledge_id}").status_code == 404


def test_a_cancelled_pledge_cannot_be_cancelled_again(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")
    pledge_id = pledge(client, request.id).json()["id"]
    client.delete(f"{API}/pledges/{pledge_id}")

    assert client.delete(f"{API}/pledges/{pledge_id}").status_code == 409


# ---------------------------------------------------------------------------------------
# What the hospital sees, and recording outcomes
# ---------------------------------------------------------------------------------------


def test_staff_see_pledged_donors_with_their_contact_details(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")
    pledge(client, request.id)

    sign_in(client, staff.email)
    response = client.get(f"{API}/requests/{request.id}/pledges")

    assert response.status_code == 200
    [item] = response.json()
    assert item["status"] == "pledged"
    assert item["donor"]["email"] == "donor1@example.com"
    assert item["donor"]["full_name"] == "Test Person"
    assert item["donor"]["blood_group"] == "O-"


def test_contact_details_are_withheld_after_a_cancellation(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")
    client.delete(f"{API}/pledges/{pledge(client, request.id).json()['id']}")

    sign_in(client, staff.email)
    [item] = client.get(f"{API}/requests/{request.id}/pledges").json()

    assert item["status"] == "cancelled"
    assert item["donor"]["email"] is None
    assert item["donor"]["full_name"] is None
    assert item["donor"]["phone"] is None


def test_another_hospital_cannot_see_or_resolve_the_pledges(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")
    pledge_id = pledge(client, request.id).json()["id"]
    other, _ = make_staff_with_hospital(db_session, email="other@example.com", name="Other")

    sign_in(client, other.email)

    assert client.get(f"{API}/requests/{request.id}/pledges").status_code == 404
    assert client.post(f"{API}/pledges/{pledge_id}/donated").status_code == 404
    assert client.post(f"{API}/pledges/{pledge_id}/no-show").status_code == 404


def test_confirming_a_donation_records_it_and_starts_the_waiting_period(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital, request = setup_request(db_session, units_needed=1)
    donor_id = make_signed_in_donor(client, email="donor1@example.com")
    pledge_id = pledge(client, request.id).json()["id"]

    sign_in(client, staff.email)
    response = client.post(f"{API}/pledges/{pledge_id}/donated")

    assert response.status_code == 200
    assert response.json()["status"] == "donated"
    assert response.json()["request_status"] == "fulfilled"

    donation = db_session.exec(select(Donation)).one()
    assert str(donation.pledge_id) == pledge_id
    assert donation.hospital_id == hospital.id
    assert donation.confirmed_by == staff.id
    donor = reload(db_session, Donor, donor_id)
    assert donor.last_donation_date == datetime.now(UTC).date()

    # The donor's dashboard now reports the waiting period.
    sign_in(client, "donor1@example.com")
    eligibility = client.get(f"{API}/donors/me/eligibility").json()
    whole_blood = next(c for c in eligibility["components"] if c["component_code"] == "whole_blood")
    assert whole_blood["eligible"] is False


def test_a_donation_never_moves_the_last_donation_date_backwards(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup_request(db_session)
    donor_id = make_signed_in_donor(client, email="donor1@example.com")
    pledge_id = pledge(client, request.id).json()["id"]
    # Simulate a later donation already on record, for example entered by an administrator.
    future = datetime.now(UTC).date() + timedelta(days=3)
    donor = db_session.get(Donor, donor_id)
    donor.last_donation_date = future
    db_session.add(donor)
    db_session.commit()

    sign_in(client, staff.email)
    client.post(f"{API}/pledges/{pledge_id}/donated")

    assert reload(db_session, Donor, donor_id).last_donation_date == future


def test_a_no_show_frees_the_unit_and_reopens_the_request(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup_request(db_session, units_needed=1)
    make_signed_in_donor(client, email="donor1@example.com")
    pledge_id = pledge(client, request.id).json()["id"]

    sign_in(client, staff.email)
    response = client.post(f"{API}/pledges/{pledge_id}/no-show")

    assert response.status_code == 200
    assert response.json()["status"] == "no_show"
    assert response.json()["request_status"] == "open"
    assert db_session.exec(select(Donation)).first() is None


def test_an_outcome_can_only_be_recorded_once(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")
    pledge_id = pledge(client, request.id).json()["id"]

    sign_in(client, staff.email)
    assert client.post(f"{API}/pledges/{pledge_id}/donated").status_code == 200

    assert client.post(f"{API}/pledges/{pledge_id}/donated").status_code == 409
    assert client.post(f"{API}/pledges/{pledge_id}/no-show").status_code == 409


def test_donors_cannot_record_outcomes(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")
    pledge_id = pledge(client, request.id).json()["id"]

    assert client.post(f"{API}/pledges/{pledge_id}/donated").status_code == 403


# ---------------------------------------------------------------------------------------
# The donor's side: open requests and history
# ---------------------------------------------------------------------------------------


def test_a_donor_sees_open_requests_they_can_answer(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, hospital, near = setup_request(db_session, recipient_group=BloodGroup.A_POSITIVE)
    # O- patients can only receive O-, so an A+ donor cannot answer this one.
    make_request_record(db_session, hospital, staff, recipient_group=BloodGroup.O_NEGATIVE)
    far_staff, far_hospital = make_staff_with_hospital(
        db_session, email="far@example.com", name="Abuja", latitude=9.0765, longitude=7.3986
    )
    make_request_record(db_session, far_hospital, far_staff, recipient_group=BloodGroup.A_POSITIVE)
    make_signed_in_donor(client, email="donor1@example.com", blood_group="A+")

    response = client.get(f"{API}/donors/me/requests")

    assert response.status_code == 200
    [item] = response.json()["items"]
    assert item["id"] == str(near.id)
    assert item["hospital"]["name"] == hospital.name
    assert item["units_remaining"] == 2
    assert item["my_pledge_id"] is None


def test_the_open_list_marks_the_donors_own_pledge(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")
    pledge_id = pledge(client, request.id).json()["id"]

    [item] = client.get(f"{API}/donors/me/requests").json()["items"]

    assert item["my_pledge_id"] == pledge_id
    assert item["units_remaining"] == 1


def test_a_donor_inside_the_waiting_period_sees_no_requests(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    setup_request(db_session)
    recent = (date.today() - timedelta(days=5)).isoformat()
    make_signed_in_donor(client, email="donor1@example.com", last_donation_date=recent)

    assert client.get(f"{API}/donors/me/requests").json()["items"] == []


def test_a_donor_sees_their_pledge_history(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup_request(db_session)
    make_signed_in_donor(client, email="donor1@example.com")
    pledge(client, request.id)

    response = client.get(f"{API}/donors/me/pledges")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    [item] = body["items"]
    assert item["status"] == PledgeStatus.PLEDGED.value
    assert item["request"]["component_name"] == "Whole blood"
    assert item["hospital"]["contact_phone"] == hospital.contact_phone
