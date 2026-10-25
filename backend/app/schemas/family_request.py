"""Request and response models for families asking a hospital for blood."""

from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.enums import BloodGroup, FamilyRequestStatus, RequestStatus, RequestUrgency
from app.schemas.common import RequiredPhone
from app.schemas.request import MAX_STANDBY_UNITS, MAX_UNITS_PER_REQUEST

# Most units a family can ask for. Larger needs (major surgery, a mass casualty) are raised
# by the hospital itself.
MAX_FAMILY_UNITS = 10


class PublicHospitalRead(BaseModel):
    """A verified hospital, as anyone looking for one can see it.

    Attributes:
        distance_km: How far it is from the position searched from, when one was given.
        postcode_ring: How close its postcode is to the postcode searched with: ``area``,
            ``district``, ``lga`` or ``state``. Empty when no postcode was given or none
            is shared.
    """

    id: UUID
    name: str
    address: str
    city: str
    state: str
    postcode: str | None
    contact_phone: str
    latitude: float
    longitude: float
    distance_km: float | None
    postcode_ring: str | None


class FamilyRequestCreate(BaseModel):
    """What a family tells a hospital when asking it to find donors.

    Attributes:
        requester_name: Who is asking.
        requester_phone: Where the hospital can call back.
        recipient_group: The patient's blood group, as the family was told it.
        component_code: What the doctor asked for. Whole blood unless they said otherwise.
        units_needed: How many units the doctor asked for.
        ward_reference: The ward, bed or lab slip number, so staff can find the patient.
        notes: Anything else the hospital should know.
        patient_is_admitted: The family confirms the patient is at this hospital. An appeal
            without this is refused, and the hospital checks it before anyone is alerted.
    """

    requester_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)
    ]
    requester_phone: RequiredPhone
    recipient_group: BloodGroup
    component_code: str = Field(default="whole_blood", min_length=1, max_length=50)
    units_needed: int = Field(ge=1, le=MAX_FAMILY_UNITS)
    ward_reference: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)
    ]
    notes: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=500)] = None
    patient_is_admitted: bool

    @model_validator(mode="after")
    def _confirmed(self) -> Self:
        if not self.patient_is_admitted:
            raise ValueError("Confirm that the patient is admitted at this hospital.")
        return self


class FamilyRequestCreated(BaseModel):
    """The answer to a family who has just asked: where to follow their appeal."""

    id: UUID
    status: FamilyRequestStatus
    hospital_name: str


class FamilyRequestTracking(BaseModel):
    """What a family sees when following their appeal. Nothing personal is included.

    Attributes:
        request_status: The state of the blood request raised from the appeal, once the
            hospital approved it.
        units_pledged: Donors who have committed so far, once approved.
    """

    id: UUID
    status: FamilyRequestStatus
    hospital_name: str
    hospital_postcode: str | None
    hospital_phone: str
    recipient_group: BloodGroup
    component_name: str
    units_needed: int
    created_at: datetime
    decided_at: datetime | None
    decline_reason: str | None
    request_status: RequestStatus | None
    units_pledged: int | None


class FamilyRequestRead(BaseModel):
    """A family's appeal as the hospital's staff see it, with the details to call back."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    requester_name: str
    requester_phone: str
    recipient_group: BloodGroup
    component_code: str
    component_name: str
    units_needed: int
    ward_reference: str
    notes: str | None
    status: FamilyRequestStatus
    created_at: datetime
    decided_at: datetime | None
    decline_reason: str | None
    blood_request_id: UUID | None


class FamilyRequestApprove(BaseModel):
    """How the hospital wants the confirmed appeal raised as a blood request.

    The patient's group, the component and the number of units come from the family's
    appeal; staff may correct the number of units after checking the patient's notes.
    """

    urgency: RequestUrgency
    deadline: datetime
    units_needed: int | None = Field(default=None, ge=1, le=MAX_UNITS_PER_REQUEST)
    standby_units: int = Field(default=0, ge=0, le=MAX_STANDBY_UNITS)
    notes: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=1000)] = None


class FamilyRequestDecline(BaseModel):
    """Why the hospital declined an appeal. Shown to the family."""

    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=500)]
