"""Tests of the donor eligibility rules.

The rules are evaluated by a pure function that takes plain values and a date, so every
boundary can be checked exactly without a database or the system clock.
"""

from datetime import date, timedelta
from uuid import uuid4

from app.models import ComponentType, Donor, DonorDeferral
from app.models.enums import BloodGroup, Sex
from app.services.eligibility import age_in_years, evaluate_eligibility

TODAY = date(2026, 10, 10)


def make_donor(**overrides: object) -> Donor:
    values: dict[str, object] = {
        "user_id": uuid4(),
        "blood_group": BloodGroup.O_NEGATIVE,
        "date_of_birth": date(1995, 6, 15),
        "weight_kg": 72.0,
        "sex": Sex.MALE,
        "latitude": 4.8,
        "longitude": 7.0,
        "city": "Port Harcourt",
        "last_donation_date": None,
    }
    values.update(overrides)
    return Donor(**values)


def whole_blood(male: int = 90, female: int = 120) -> ComponentType:
    return ComponentType(
        code="whole_blood",
        name="Whole blood",
        min_interval_days_male=male,
        min_interval_days_female=female,
    )


def platelets(days: int = 14) -> ComponentType:
    return ComponentType(
        code="platelets",
        name="Platelets",
        min_interval_days_male=days,
        min_interval_days_female=days,
    )


def evaluate(donor: Donor, components: list[ComponentType], deferrals=(), today=TODAY):
    return evaluate_eligibility(
        donor,
        components,
        list(deferrals),
        today=today,
        min_age_years=18,
        max_age_years=65,
        min_weight_kg=50.0,
    )


def test_a_donor_who_has_never_donated_is_eligible() -> None:
    result = evaluate(make_donor(), [whole_blood()])

    assert result.eligible_for_any is True
    assert result.components[0].eligible is True
    assert result.components[0].next_eligible_date is None
    assert result.blockers == ()


def test_the_day_the_waiting_period_ends_counts_as_eligible() -> None:
    donor = make_donor(last_donation_date=TODAY - timedelta(days=90))

    assert evaluate(donor, [whole_blood()]).components[0].eligible is True


def test_one_day_early_is_not_eligible_and_reports_the_date() -> None:
    donor = make_donor(last_donation_date=TODAY - timedelta(days=89))

    component = evaluate(donor, [whole_blood()]).components[0]

    assert component.eligible is False
    assert component.next_eligible_date == TODAY + timedelta(days=1)


def test_female_donors_use_the_female_interval() -> None:
    last = TODAY - timedelta(days=100)  # past the male interval, short of the female one
    male = make_donor(sex=Sex.MALE, last_donation_date=last)
    female = make_donor(sex=Sex.FEMALE, last_donation_date=last)

    assert evaluate(male, [whole_blood()]).components[0].eligible is True
    assert evaluate(female, [whole_blood()]).components[0].eligible is False


def test_changing_the_interval_in_the_data_changes_the_result() -> None:
    """The rule lives in the component data, so editing it needs no code change."""
    donor = make_donor(last_donation_date=TODAY - timedelta(days=60))

    assert evaluate(donor, [whole_blood(male=90)]).components[0].eligible is False
    assert evaluate(donor, [whole_blood(male=56)]).components[0].eligible is True


def test_components_are_judged_independently() -> None:
    donor = make_donor(last_donation_date=TODAY - timedelta(days=20))

    result = evaluate(donor, [whole_blood(), platelets(14)])
    by_code = {item.code: item for item in result.components}

    assert by_code["whole_blood"].eligible is False
    assert by_code["platelets"].eligible is True
    assert result.eligible_for_any is True


def test_age_is_counted_in_whole_years_and_the_birthday_counts() -> None:
    assert age_in_years(date(2008, 10, 10), date(2026, 10, 10)) == 18
    assert age_in_years(date(2008, 10, 11), date(2026, 10, 10)) == 17


def test_a_donor_turning_eighteen_today_is_eligible() -> None:
    assert evaluate(make_donor(date_of_birth=date(2008, 10, 10)), [whole_blood()]).eligible_for_any


def test_a_donor_one_day_short_of_eighteen_is_blocked() -> None:
    result = evaluate(make_donor(date_of_birth=date(2008, 10, 11)), [whole_blood()])

    assert result.eligible_for_any is False
    assert any("at least 18" in blocker for blocker in result.blockers)
    assert result.components[0].next_eligible_date is None


def test_donors_over_the_maximum_age_are_blocked() -> None:
    result = evaluate(make_donor(date_of_birth=date(1950, 1, 1)), [whole_blood()])

    assert result.eligible_for_any is False
    assert any("65" in blocker for blocker in result.blockers)


def test_underweight_donors_are_blocked() -> None:
    result = evaluate(make_donor(weight_kg=49.9), [whole_blood()])

    assert result.eligible_for_any is False
    assert any("50 kg" in blocker for blocker in result.blockers)


def test_donors_at_the_minimum_weight_are_accepted() -> None:
    assert evaluate(make_donor(weight_kg=50.0), [whole_blood()]).eligible_for_any is True


def test_an_active_deferral_blocks_and_sets_the_next_date_to_the_day_after() -> None:
    deferral = DonorDeferral(
        donor_id=uuid4(), reason="Recent illness", deferred_until=TODAY + timedelta(days=5),
        recorded_by=uuid4(),
    )

    result = evaluate(make_donor(), [whole_blood()], [deferral])

    assert result.eligible_for_any is False
    assert result.components[0].next_eligible_date == TODAY + timedelta(days=6)


def test_a_deferral_ending_today_still_applies() -> None:
    deferral = DonorDeferral(
        donor_id=uuid4(), reason="Medication", deferred_until=TODAY, recorded_by=uuid4()
    )

    assert evaluate(make_donor(), [whole_blood()], [deferral]).eligible_for_any is False


def test_an_expired_deferral_is_ignored() -> None:
    deferral = DonorDeferral(
        donor_id=uuid4(),
        reason="Recent illness",
        deferred_until=TODAY - timedelta(days=1),
        recorded_by=uuid4(),
    )

    assert evaluate(make_donor(), [whole_blood()], [deferral]).eligible_for_any is True


def test_a_permanent_deferral_blocks_with_no_date() -> None:
    deferral = DonorDeferral(
        donor_id=uuid4(), reason="Medical advice", deferred_until=None, recorded_by=uuid4()
    )

    result = evaluate(make_donor(), [whole_blood()], [deferral])

    assert result.eligible_for_any is False
    assert result.components[0].next_eligible_date is None


def test_the_next_date_is_the_later_of_the_interval_and_the_deferral() -> None:
    deferral = DonorDeferral(
        donor_id=uuid4(), reason="Recent illness", deferred_until=TODAY + timedelta(days=40),
        recorded_by=uuid4(),
    )
    donor = make_donor(last_donation_date=TODAY - timedelta(days=60))  # interval ends in 30

    result = evaluate(donor, [whole_blood()], [deferral])

    assert result.components[0].next_eligible_date == TODAY + timedelta(days=41)
