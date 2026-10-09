"""Request and response models for blood requests and donor matches."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, BeforeValidator, Field, field_validator

from app.models.enums import BloodGroup, RequestStatus, RequestUrgency
from app.schemas.common import blank_to_none

# Limits on what a request may ask for. They protect donors from alert floods and keep a
# request meaningful: a deadline far in the future is not an urgent need.
MAX_UNITS_PER_REQUEST = 20
MAX_DEADLINE_DAYS = 30
MIN_DEADLINE_MINUTES = 5
MAX_NOTES_LENGTH = 1000
MAX_SEARCH_RADIUS_KM = 200.0


def _check_notes(value: str | None) -> str | None:
    if value is not None and len(value) > MAX_NOTES_LENGTH:
        raise ValueError(f"Notes must be at most {MAX_NOTES_LENGTH} characters.")
    return value


_Notes = Annotated[
    str | None,
    BeforeValidator(blank_to_none),
    AfterValidator(_check_notes),
]


class RequestCreate(BaseModel):
    """What a verified hospital supplies to ask for blood.

    Attributes:
        recipient_group: Blood group of the patient. Compatible donor groups are derived
            from the compatibility table.
        component_code: What is needed, such as ``whole_blood`` or ``platelets``.
        units_needed: How many units are still required.
        urgency: How quickly the blood is needed.
        deadline: When the need ends. Must carry a time zone, so it means the same moment
            everywhere, and lie between five minutes and thirty days from now.
        notes: Optional context for donors, such as the ward or the desk to report to.
    """

    recipient_group: BloodGroup
    component_code: str = Field(default="whole_blood", min_length=1, max_length=50)
    units_needed: int = Field(ge=1, le=MAX_UNITS_PER_REQUEST)
    urgency: RequestUrgency
    deadline: datetime
    notes: _Notes = None

    @field_validator("deadline")
    @classmethod
    def _reasonable_deadline(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "Deadline must include a time zone, for example 2026-10-12T18:00:00Z."
            )
        now = datetime.now(UTC)
        if value <= now + timedelta(minutes=MIN_DEADLINE_MINUTES):
            raise ValueError(
                f"Deadline must be at least {MIN_DEADLINE_MINUTES} minutes from now."
            )
        if value > now + timedelta(days=MAX_DEADLINE_DAYS):
            raise ValueError(f"Deadline cannot be more than {MAX_DEADLINE_DAYS} days away.")
        return value.astimezone(UTC)


class RequestRead(BaseModel):
    """A blood request as shown to the staff of the hospital that raised it.

    ``units_pledged`` counts donors who have committed or have already given;
    ``units_remaining`` is what is still needed.
    """

    id: UUID
    hospital_id: UUID
    recipient_group: BloodGroup
    component_code: str
    component_name: str
    units_needed: int
    units_pledged: int
    units_remaining: int
    urgency: RequestUrgency
    deadline: datetime
    notes: str | None
    status: RequestStatus
    fulfilled_at: datetime | None
    created_at: datetime


class RequestPage(BaseModel):
    """One page of a hospital's requests."""

    items: list[RequestRead]
    total: int
    limit: int
    offset: int


class MatchRead(BaseModel):
    """A donor who can answer a request.

    Deliberately anonymous: no name, phone number, email or exact location. A hospital sees
    a donor's contact details only after that donor pledges.
    """

    donor_id: UUID
    blood_group: BloodGroup
    city: str
    distance_km: float


class MatchesResponse(BaseModel):
    """The donors matching a request, nearest first."""

    items: list[MatchRead]
    total: int
    radius_km: float
