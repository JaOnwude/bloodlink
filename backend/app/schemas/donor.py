"""Request and response models for donor profiles and eligibility."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models.enums import BloodGroup, Sex

# Dates typed by people in Nigeria (UTC+1) can be a day ahead of the server's UTC date for
# a short time around midnight. Allowing one day of slack stops "today" being rejected as
# "in the future" during that window.
_FUTURE_TOLERANCE = timedelta(days=1)

# Oldest birth date accepted, as an age in years. Anything beyond this is a typing error.
_MAX_PLAUSIBLE_AGE_YEARS = 120


def _today() -> date:
    return datetime.now(UTC).date()


class DonorWrite(BaseModel):
    """The donor's own description of themselves, used to create or replace the profile.

    Attributes:
        blood_group: ABO/Rh group.
        date_of_birth: Used to check the permitted age range.
        weight_kg: Body weight, used to check the minimum weight.
        sex: Selects the applicable interval between donations.
        latitude: Approximate latitude used to rank nearby requests.
        longitude: Approximate longitude.
        city: Shown to hospital staff once the donor pledges.
        last_donation_date: When the donor last gave blood, as they remember it. It is
            self-declared until a hospital confirms a donation, and final eligibility is
            always decided clinically at the donation site.
        is_available: Switch to pause alerts without deleting the profile.
        consent_to_contact: Explicit permission to be contacted about requests. Without it
            the donor is never matched.
    """

    blood_group: BloodGroup
    date_of_birth: date
    weight_kg: float = Field(gt=0, le=400)
    sex: Sex
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    city: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    last_donation_date: date | None = None
    is_available: bool = True
    consent_to_contact: bool = False

    @field_validator("date_of_birth")
    @classmethod
    def _plausible_birth_date(cls, value: date) -> date:
        today = _today()
        if value > today + _FUTURE_TOLERANCE:
            raise ValueError("Date of birth cannot be in the future.")
        if value.year < today.year - _MAX_PLAUSIBLE_AGE_YEARS:
            raise ValueError("Enter a valid date of birth.")
        return value

    @field_validator("last_donation_date")
    @classmethod
    def _not_in_the_future(cls, value: date | None) -> date | None:
        if value is not None and value > _today() + _FUTURE_TOLERANCE:
            raise ValueError("Last donation date cannot be in the future.")
        return value

    @model_validator(mode="after")
    def _donation_after_birth(self) -> Self:
        if self.last_donation_date is not None and self.last_donation_date < self.date_of_birth:
            raise ValueError("Last donation date cannot be before the date of birth.")
        return self


class AvailabilityUpdate(BaseModel):
    """Switch alerts on or off without touching the rest of the profile."""

    is_available: bool


class DonorRead(BaseModel):
    """The donor's own profile as stored."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    blood_group: BloodGroup
    date_of_birth: date
    weight_kg: float
    sex: Sex
    latitude: float
    longitude: float
    city: str
    last_donation_date: date | None
    is_available: bool
    consent_to_contact: bool


class ComponentEligibilityRead(BaseModel):
    """Whether the donor can give one kind of donation, and if not, from when.

    Attributes:
        component_code: Machine identifier such as ``whole_blood``.
        component_name: Human-readable name.
        eligible: True when the donor may give this component today.
        next_eligible_date: The first day they may give it, when that can be worked out.
            Empty when they are already eligible or when no date applies.
    """

    component_code: str
    component_name: str
    eligible: bool
    next_eligible_date: date | None


class EligibilityRead(BaseModel):
    """The donor's eligibility today.

    Attributes:
        eligible_for_any: True when at least one component can be given today.
        blockers: Reasons that stop every donation (age, weight, deferrals).
        components: The position for each donatable component.
    """

    eligible_for_any: bool
    blockers: list[str]
    components: list[ComponentEligibilityRead]
