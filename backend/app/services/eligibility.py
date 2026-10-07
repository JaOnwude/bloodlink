"""Donor eligibility rules.

Whether someone may donate depends on rules that live in data and configuration, not in
code: the waiting period between donations is stored per component (and per sex) in the
``component_types`` table, and the age and weight limits come from the settings. Changing
a rule therefore never requires changing this module.

The core function, ``evaluate_eligibility``, is deliberately pure. It takes plain values
and a date, touches no database and reads no clock, so every rule can be tested exactly,
including the boundary days.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.models import ComponentType, Donor, DonorDeferral
from app.models.enums import Sex


@dataclass(frozen=True)
class ComponentEligibility:
    """The donor's position for one component.

    Attributes:
        code: Machine identifier of the component.
        name: Human-readable name.
        eligible: True when the donor may give this component on the evaluated day.
        next_eligible_date: The first day they may give it, when one can be worked out.
            None when they are already eligible, or when no date applies (for example a
            permanent deferral or an age limit).
    """

    code: str
    name: str
    eligible: bool
    next_eligible_date: date | None


@dataclass(frozen=True)
class EligibilityResult:
    """The outcome of evaluating a donor against every active component.

    Attributes:
        blockers: Plain-language reasons that stop every kind of donation.
        components: One entry per component, in the order supplied.
    """

    blockers: tuple[str, ...]
    components: tuple[ComponentEligibility, ...]

    @property
    def eligible_for_any(self) -> bool:
        """True when at least one component can be given today."""
        return any(component.eligible for component in self.components)


def age_in_years(born: date, today: date) -> int:
    """Whole years between ``born`` and ``today``; the birthday itself counts as a new year."""
    years = today.year - born.year
    if (today.month, today.day) < (born.month, born.day):
        years -= 1
    return years


def evaluate_eligibility(
    donor: Donor,
    components: Sequence[ComponentType],
    deferrals: Sequence[DonorDeferral],
    *,
    today: date,
    min_age_years: int,
    max_age_years: int,
    min_weight_kg: float,
) -> EligibilityResult:
    """Work out what a donor may give on a particular day.

    A donor is eligible for a component when no general blocker applies (age, weight, an
    active deferral) and the waiting period for that component, which depends on the donor's
    sex, has passed. The day the waiting period ends counts as eligible.

    Args:
        donor: The donor's profile.
        components: The donatable components to evaluate, with their intervals.
        deferrals: The donor's recorded deferrals, current or past.
        today: The day to evaluate. Passed in so the result is reproducible.
        min_age_years: Youngest permitted age.
        max_age_years: Oldest permitted age.
        min_weight_kg: Lowest permitted body weight.

    Returns:
        The general blockers and the position for each component.
    """
    blockers: list[str] = []
    # Reasons that make a "next eligible date" meaningless (the donor cannot simply wait).
    cannot_wait = False

    age = age_in_years(donor.date_of_birth, today)
    if age < min_age_years:
        blockers.append(f"Donors must be at least {min_age_years} years old.")
        cannot_wait = True
    elif age > max_age_years:
        blockers.append(f"Donors must be {max_age_years} years old or younger.")
        cannot_wait = True

    if donor.weight_kg < min_weight_kg:
        blockers.append(f"Donors must weigh at least {min_weight_kg:g} kg.")
        cannot_wait = True

    # A deferral ending on a given date still applies on that date; the first free day is
    # the day after. A deferral without an end date is permanent.
    first_day_after_deferrals: date | None = None
    for deferral in deferrals:
        if deferral.deferred_until is None:
            blockers.append("You are permanently deferred from donating.")
            cannot_wait = True
        elif deferral.deferred_until >= today:
            blockers.append(f"You are deferred from donating until {deferral.deferred_until}.")
            free_from = deferral.deferred_until + timedelta(days=1)
            if first_day_after_deferrals is None or free_from > first_day_after_deferrals:
                first_day_after_deferrals = free_from

    results: list[ComponentEligibility] = []
    for component in components:
        interval_days = (
            component.min_interval_days_male
            if donor.sex == Sex.MALE
            else component.min_interval_days_female
        )
        interval_ends = (
            donor.last_donation_date + timedelta(days=interval_days)
            if donor.last_donation_date is not None
            else None
        )
        waiting_period_over = interval_ends is None or today >= interval_ends
        eligible = not blockers and waiting_period_over

        next_date: date | None = None
        if not eligible and not cannot_wait:
            candidates = [d for d in (interval_ends, first_day_after_deferrals) if d is not None]
            next_date = max(candidates) if candidates else None

        results.append(
            ComponentEligibility(
                code=component.code,
                name=component.name,
                eligible=eligible,
                next_eligible_date=next_date,
            )
        )

    return EligibilityResult(blockers=tuple(blockers), components=tuple(results))


def get_donor_eligibility(
    session: Session, donor: Donor, *, today: date | None = None
) -> EligibilityResult:
    """Load the rules and the donor's deferrals from the database and evaluate them.

    Args:
        session: An open database session.
        donor: The donor to evaluate.
        today: The day to evaluate; defaults to the current UTC date.
    """
    settings = get_settings()
    components = session.exec(
        select(ComponentType).where(col(ComponentType.is_active).is_(True)).order_by(
            col(ComponentType.code)
        )
    ).all()
    deferrals = session.exec(select(DonorDeferral).where(DonorDeferral.donor_id == donor.id)).all()
    return evaluate_eligibility(
        donor,
        components,
        deferrals,
        today=today or datetime.now(UTC).date(),
        min_age_years=settings.min_donor_age_years,
        max_age_years=settings.max_donor_age_years,
        min_weight_kg=settings.min_donor_weight_kg,
    )
