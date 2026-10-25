"""Tests of bringing an older demonstration database up to date, against a real database."""

import pytest
from sqlmodel import Session, col, select

from app.db.demo_refresh import DemoNotSeededError, refresh_demo_data
from app.db.demo_seed import DEMO_DOMAIN, seed_demo_data, staff_email
from app.models import BloodRequest, Donor, Hospital, User
from app.models.enums import RequestStatus
from tests.helpers import PASSWORD, make_donor_record

PHONE = "+2348099990000"


@pytest.fixture
def old_demo(db_session: Session) -> Session:
    """A demonstration seeded before postcodes existed: every postcode removed."""
    seed_demo_data(db_session, password=PASSWORD)
    for hospital in db_session.exec(select(Hospital)).all():
        hospital.postcode = None
        db_session.add(hospital)
    for donor in db_session.exec(select(Donor)).all():
        donor.postcode_area = None
        db_session.add(donor)
    db_session.commit()
    return db_session


def _abuja_hospital(session: Session) -> Hospital:
    staff = session.exec(select(User).where(User.email == staff_email("abuja"))).one()
    hospital = session.get(Hospital, staff.hospital_id)
    assert hospital is not None
    return hospital


def test_the_abuja_hospital_and_donors_get_their_sample_postcodes(old_demo: Session) -> None:
    summary = refresh_demo_data(old_demo)

    assert summary.hospital_postcodes == 1
    assert summary.donor_postcodes == 8
    assert _abuja_hospital(old_demo).postcode == "FC-01-A01-KP-27"
    areas = old_demo.exec(select(Donor.postcode_area).where(Donor.city == "Abuja")).all()
    assert all(area and area.startswith("FC-01-A01-") for area in areas)


def test_a_fresh_request_is_raised_when_none_is_open_long_enough(old_demo: Session) -> None:
    hospital = _abuja_hospital(old_demo)
    for request in old_demo.exec(
        select(BloodRequest).where(BloodRequest.hospital_id == hospital.id)
    ).all():
        request.status = RequestStatus.CLOSED
        old_demo.add(request)
    old_demo.commit()

    summary = refresh_demo_data(old_demo)

    assert summary.request_raised is True
    open_requests = old_demo.exec(
        select(BloodRequest).where(
            BloodRequest.hospital_id == hospital.id, BloodRequest.status == RequestStatus.OPEN
        )
    ).all()
    assert len(open_requests) == 1


def test_running_it_twice_changes_nothing_the_second_time(old_demo: Session) -> None:
    refresh_demo_data(old_demo)
    requests_after_first = len(old_demo.exec(select(BloodRequest)).all())

    again = refresh_demo_data(old_demo)

    assert again.hospital_postcodes == 0
    assert again.donor_postcodes == 0
    assert again.request_raised is False
    assert len(old_demo.exec(select(BloodRequest)).all()) == requests_after_first


def test_the_phone_goes_to_the_donor_who_comes_first_for_the_request(old_demo: Session) -> None:
    summary = refresh_demo_data(old_demo, donor_phone=PHONE)

    assert summary.phone_donor is not None
    user = old_demo.exec(select(User).where(User.email == summary.phone_donor)).one()
    assert user.phone == PHONE
    donor = old_demo.exec(select(Donor).where(Donor.user_id == user.id)).one()
    assert donor.city == "Abuja"


def test_without_a_phone_no_phone_number_changes(old_demo: Session) -> None:
    phones_before = old_demo.exec(select(User.phone)).all()

    summary = refresh_demo_data(old_demo)

    assert summary.phone_donor is None
    assert old_demo.exec(select(User.phone)).all() == phones_before


def test_records_outside_the_demonstration_are_never_touched(old_demo: Session) -> None:
    outsider = make_donor_record(old_demo, email="real@example.com", city="Abuja")

    refresh_demo_data(old_demo, donor_phone=PHONE)

    old_demo.refresh(outsider)
    assert outsider.postcode_area is None
    real_user = old_demo.exec(select(User).where(User.email == "real@example.com")).one()
    assert real_user.phone is None
    assert old_demo.exec(select(User).where(col(User.email).endswith(f"@{DEMO_DOMAIN}"))).first()


def test_an_empty_database_is_refused(db_session: Session) -> None:
    with pytest.raises(DemoNotSeededError):
        refresh_demo_data(db_session)
