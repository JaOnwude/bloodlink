"""Request and response models for hospitals and their verification."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
)

from app.models.enums import VerificationStatus
from app.schemas.common import RequiredPhone, blank_to_none

_Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
_Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)]
_Place = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]

_MAX_REGISTRATION_NUMBER_LENGTH = 100


def _check_registration_number(value: str | None) -> str | None:
    if value is not None and len(value) > _MAX_REGISTRATION_NUMBER_LENGTH:
        raise ValueError(
            f"Registration number must be at most {_MAX_REGISTRATION_NUMBER_LENGTH} characters."
        )
    return value


# Blank input means "not provided" and is stored as nothing rather than as an empty string.
_RegistrationNumber = Annotated[
    str | None,
    BeforeValidator(blank_to_none),
    AfterValidator(_check_registration_number),
]


class HospitalWrite(BaseModel):
    """Details a hospital staff member supplies to register or update their facility.

    Attributes:
        name: Official facility name.
        address: Street address.
        city: City or town.
        state: State or equivalent region.
        latitude: Facility latitude, the origin for donor searches.
        longitude: Facility longitude.
        registration_number: Regulator-issued registration or licence number, if any.
        contact_phone: Number of the switchboard or blood bank desk.
    """

    name: _Name
    address: _Address
    city: _Place
    state: _Place
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    registration_number: _RegistrationNumber = None
    contact_phone: RequiredPhone


class HospitalRead(BaseModel):
    """A hospital as shown to its own staff.

    ``rejection_reason`` explains a rejection so the facility can correct and resubmit.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str
    city: str
    state: str
    latitude: float
    longitude: float
    registration_number: str | None
    contact_phone: str
    verification_status: VerificationStatus
    verified_at: datetime | None
    rejection_reason: str | None
    created_at: datetime


class StaffSummary(BaseModel):
    """A staff member linked to a hospital, shown to administrators reviewing it."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str
    phone: str | None


class AdminHospitalRead(HospitalRead):
    """A hospital as shown to administrators, with the people who registered it."""

    staff: list[StaffSummary]


class HospitalPage(BaseModel):
    """One page of hospitals for the administrator's review queue."""

    items: list[AdminHospitalRead]
    total: int
    limit: int
    offset: int


class RejectRequest(BaseModel):
    """The reason an administrator gives when rejecting or revoking a hospital."""

    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)]
