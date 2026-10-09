"""Tests of the donor matching engine against a real database.

These cover the third hard part of the project: compatibility from the rules table,
eligibility, availability, consent, distance and ordering. They need the reference data
(compatibility chart and component types).
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.models import ComponentType, DonorDeferral, Pledge
from app.models.enums import BloodGroup, PledgeStatus
from app.services.matching import find_matches
from tests.helpers import make_donor_record, make_request_record, make_staff_with_hospital

# Roughly 11 km of latitude per tenth of a degree.
TENTH_DEGREE_KM = 11.1


def today():
    return datetime.now(UTC).date()


def search(db_session: Session, request, hospital, *, radius_km: float = 25.0, limit: int = 50):
    return find_matches(db_session, request, hospital, radius_km=radius_km, limit=limit)


def setup(db_session: Session, **request_overrides):
    staff, hospital = make_staff_with_hospital(db_session)
    request = make_request_record(db_session, hospital, staff, **request_overrides)
    return staff, hospital, request


def groups_of(matches) -> set[BloodGroup]:
    return {match.donor.blood_group for match in matches}


def whole_blood_interval(db_session: Session) -> int:
    component = db_session.exec(
        select(ComponentType).where(ComponentType.code == "whole_blood")
    ).one()
    return component.min_interval_days_male


# ---------------------------------------------------------------------------------------
# Compatibility comes from the rules table
# ---------------------------------------------------------------------------------------


# The red-cell compatibility chart, typed out independently of the seed data, so the test
# checks the rules table against the published chart rather than against itself.
_CHART: dict[BloodGroup, set[BloodGroup]] = {
    BloodGroup.O_NEGATIVE: {BloodGroup.O_NEGATIVE},
    BloodGroup.O_POSITIVE: {BloodGroup.O_POSITIVE, BloodGroup.O_NEGATIVE},
    BloodGroup.A_NEGATIVE: {BloodGroup.A_NEGATIVE, BloodGroup.O_NEGATIVE},
    BloodGroup.A_POSITIVE: {
        BloodGroup.A_POSITIVE,
        BloodGroup.A_NEGATIVE,
        BloodGroup.O_POSITIVE,
        BloodGroup.O_NEGATIVE,
    },
    BloodGroup.B_NEGATIVE: {BloodGroup.B_NEGATIVE, BloodGroup.O_NEGATIVE},
    BloodGroup.B_POSITIVE: {
        BloodGroup.B_POSITIVE,
        BloodGroup.B_NEGATIVE,
        BloodGroup.O_POSITIVE,
        BloodGroup.O_NEGATIVE,
    },
    BloodGroup.AB_NEGATIVE: {
        BloodGroup.AB_NEGATIVE,
        BloodGroup.A_NEGATIVE,
        BloodGroup.B_NEGATIVE,
        BloodGroup.O_NEGATIVE,
    },
    BloodGroup.AB_POSITIVE: set(BloodGroup),
}


@pytest.mark.parametrize("recipient", list(BloodGroup), ids=lambda group: group.value)
def test_every_recipient_group_matches_exactly_the_charted_donor_groups(
    db_session: Session, reference_data: None, recipient: BloodGroup
) -> None:
    _, hospital, request = setup(db_session, recipient_group=recipient)
    for number, group in enumerate(BloodGroup):
        make_donor_record(db_session, email=f"d{number}@example.com", blood_group=group)

    matches, _ = search(db_session, request, hospital)

    assert groups_of(matches) == _CHART[recipient]


def test_o_negative_patients_match_only_o_negative_donors(
    db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session, recipient_group=BloodGroup.O_NEGATIVE)
    for number, group in enumerate(BloodGroup):
        make_donor_record(db_session, email=f"d{number}@example.com", blood_group=group)

    matches, total = search(db_session, request, hospital)

    assert groups_of(matches) == {BloodGroup.O_NEGATIVE}
    assert total == 1


def test_ab_positive_patients_match_every_group(
    db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session, recipient_group=BloodGroup.AB_POSITIVE)
    for number, group in enumerate(BloodGroup):
        make_donor_record(db_session, email=f"d{number}@example.com", blood_group=group)

    matches, _ = search(db_session, request, hospital)

    assert groups_of(matches) == set(BloodGroup)


def test_a_positive_patients_match_a_and_o_groups_only(
    db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session, recipient_group=BloodGroup.A_POSITIVE)
    for number, group in enumerate(BloodGroup):
        make_donor_record(db_session, email=f"d{number}@example.com", blood_group=group)

    matches, _ = search(db_session, request, hospital)

    assert groups_of(matches) == {
        BloodGroup.A_POSITIVE,
        BloodGroup.A_NEGATIVE,
        BloodGroup.O_POSITIVE,
        BloodGroup.O_NEGATIVE,
    }


# ---------------------------------------------------------------------------------------
# Distance and ordering
# ---------------------------------------------------------------------------------------


def test_donors_outside_the_radius_are_excluded(
    db_session: Session, reference_data: None
) -> None:
    staff, hospital, request = setup(db_session)
    near = make_donor_record(
        db_session, email="near@example.com", latitude=hospital.latitude + 0.09
    )
    make_donor_record(db_session, email="far@example.com", latitude=hospital.latitude + 0.6)

    matches, total = search(db_session, request, hospital, radius_km=25)

    assert [match.donor.id for match in matches] == [near.id]
    assert total == 1


def test_a_wider_radius_includes_more_donors(db_session: Session, reference_data: None) -> None:
    _, hospital, request = setup(db_session)
    make_donor_record(db_session, email="far@example.com", latitude=hospital.latitude + 0.6)

    assert search(db_session, request, hospital, radius_km=25)[1] == 0
    assert search(db_session, request, hospital, radius_km=100)[1] == 1


def test_matches_are_ordered_nearest_first(db_session: Session, reference_data: None) -> None:
    _, hospital, request = setup(db_session)
    for city, offset in (("Far", 0.15), ("Near", 0.05), ("Mid", 0.10)):
        make_donor_record(
            db_session,
            email=f"{city}@example.com",
            city=city,
            latitude=hospital.latitude + offset,
        )

    matches, _ = search(db_session, request, hospital)

    assert [match.donor.city for match in matches] == ["Near", "Mid", "Far"]
    distances = [match.distance_km for match in matches]
    assert distances == sorted(distances)
    assert distances[0] == pytest.approx(TENTH_DEGREE_KM / 2, abs=0.2)


def test_the_limit_applies_but_the_total_counts_every_match(
    db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session)
    for number in range(5):
        make_donor_record(db_session, email=f"d{number}@example.com")

    matches, total = search(db_session, request, hospital, limit=2)

    assert len(matches) == 2
    assert total == 5


# ---------------------------------------------------------------------------------------
# Willingness
# ---------------------------------------------------------------------------------------


def test_donors_who_paused_alerts_are_excluded(db_session: Session, reference_data: None) -> None:
    _, hospital, request = setup(db_session)
    make_donor_record(db_session, email="paused@example.com", is_available=False)

    assert search(db_session, request, hospital)[1] == 0


def test_donors_who_did_not_consent_are_excluded(
    db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session)
    make_donor_record(db_session, email="private@example.com", consent=False)

    assert search(db_session, request, hospital)[1] == 0


def test_deactivated_accounts_are_excluded(db_session: Session, reference_data: None) -> None:
    _, hospital, request = setup(db_session)
    make_donor_record(db_session, email="gone@example.com", is_active=False)

    assert search(db_session, request, hospital)[1] == 0


def test_donors_with_a_pledge_waiting_to_be_resolved_are_excluded(
    db_session: Session, reference_data: None
) -> None:
    staff, hospital, request = setup(db_session)
    other = make_request_record(db_session, hospital, staff)
    busy = make_donor_record(db_session, email="busy@example.com")
    free = make_donor_record(db_session, email="free@example.com")
    db_session.add(Pledge(request_id=other.id, donor_id=busy.id))
    # A cancelled pledge no longer ties the donor up.
    db_session.add(Pledge(request_id=other.id, donor_id=free.id, status=PledgeStatus.CANCELLED))
    db_session.commit()

    matches, total = search(db_session, request, hospital)

    assert total == 1
    assert matches[0].donor.id == free.id


# ---------------------------------------------------------------------------------------
# Eligibility rules apply to matching
# ---------------------------------------------------------------------------------------


def test_a_donor_who_gave_yesterday_is_excluded(
    db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session)
    make_donor_record(
        db_session, email="recent@example.com", last_donation_date=today() - timedelta(days=1)
    )

    assert search(db_session, request, hospital)[1] == 0


def test_a_donor_whose_waiting_period_ends_today_is_included(
    db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session)
    interval = whole_blood_interval(db_session)
    make_donor_record(
        db_session,
        email="boundary@example.com",
        last_donation_date=today() - timedelta(days=interval),
    )

    assert search(db_session, request, hospital)[1] == 1


def test_a_donor_one_day_short_of_the_waiting_period_is_excluded(
    db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session)
    interval = whole_blood_interval(db_session)
    make_donor_record(
        db_session,
        email="early@example.com",
        last_donation_date=today() - timedelta(days=interval - 1),
    )

    assert search(db_session, request, hospital)[1] == 0


def test_an_active_deferral_excludes_an_otherwise_eligible_donor(
    db_session: Session, reference_data: None
) -> None:
    staff, hospital, request = setup(db_session)
    donor = make_donor_record(db_session, email="deferred@example.com")
    db_session.add(
        DonorDeferral(
            donor_id=donor.id,
            reason="Recent illness",
            deferred_until=today() + timedelta(days=5),
            recorded_by=staff.id,
        )
    )
    db_session.commit()

    assert search(db_session, request, hospital)[1] == 0


def test_underage_and_underweight_donors_are_excluded(
    db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session)
    make_donor_record(
        db_session, email="young@example.com", date_of_birth=today() - timedelta(days=365 * 10)
    )
    make_donor_record(db_session, email="light@example.com", weight_kg=40)

    assert search(db_session, request, hospital)[1] == 0


def test_each_component_uses_its_own_waiting_period(
    db_session: Session, reference_data: None
) -> None:
    """A donor can be eligible for platelets while still waiting to give whole blood."""
    components = {
        component.code: component for component in db_session.exec(select(ComponentType)).all()
    }
    whole = components["whole_blood"].min_interval_days_male
    platelets = components["platelets"].min_interval_days_male
    if platelets >= whole:
        pytest.skip("Needs a platelet waiting period shorter than whole blood's.")

    staff, hospital = make_staff_with_hospital(db_session)
    make_donor_record(
        db_session,
        email="mixed@example.com",
        last_donation_date=today() - timedelta(days=platelets),
    )
    whole_request = make_request_record(db_session, hospital, staff, component_code="whole_blood")
    platelet_request = make_request_record(db_session, hospital, staff, component_code="platelets")

    assert search(db_session, whole_request, hospital)[1] == 0
    assert search(db_session, platelet_request, hospital)[1] == 1
