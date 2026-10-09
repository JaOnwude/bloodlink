"""Response models for pledges, and for the requests a donor can answer.

Two audiences see pledges, and each sees only what it needs:

* hospital staff see who pledged to their request, with the donor's name and phone number,
  because the donor chose to share them by pledging;
* a donor sees their own pledges with the hospital's name, address and phone number, so
  they know where to go and whom to call.

A donor never sees another donor, and the open requests offered to a donor show the
hospital, not other people who have pledged.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import BloodGroup, PledgeStatus, RequestStatus, RequestUrgency


class PledgeRead(BaseModel):
    """A pledge after a change, with the effect on its request.

    Attributes:
        request_status: The request's state after the change, for example ``fulfilled``
            when this pledge took the last unit.
        units_remaining: Units the request still needs after the change.
    """

    id: UUID
    request_id: UUID
    status: PledgeStatus
    pledged_at: datetime
    resolved_at: datetime | None
    request_status: RequestStatus
    units_remaining: int


class PledgedDonor(BaseModel):
    """The donor behind a pledge, as the hospital sees them.

    The contact fields are empty for a cancelled pledge: the donor withdrew, and with it
    the permission to be contacted about this request.
    """

    donor_id: UUID
    blood_group: BloodGroup
    city: str
    full_name: str | None
    phone: str | None
    email: str | None


class HospitalPledgeRead(BaseModel):
    """A pledge to one of the hospital's requests."""

    id: UUID
    status: PledgeStatus
    pledged_at: datetime
    resolved_at: datetime | None
    donor: PledgedDonor


class HospitalSummary(BaseModel):
    """Where to go and whom to call, as shown to a donor."""

    id: UUID
    name: str
    address: str
    city: str
    state: str
    contact_phone: str
    latitude: float
    longitude: float


class DonorRequestSummary(BaseModel):
    """The request a donor's pledge is for."""

    id: UUID
    recipient_group: BloodGroup
    component_name: str
    urgency: RequestUrgency
    deadline: datetime
    notes: str | None
    status: RequestStatus


class DonorPledgeRead(BaseModel):
    """One of the donor's own pledges."""

    id: UUID
    status: PledgeStatus
    pledged_at: datetime
    resolved_at: datetime | None
    request: DonorRequestSummary
    hospital: HospitalSummary


class DonorPledgePage(BaseModel):
    """One page of the donor's pledges, most recent first."""

    items: list[DonorPledgeRead]
    total: int
    limit: int
    offset: int


class OpenRequestForDonor(BaseModel):
    """An open request the donor can answer.

    Attributes:
        distance_km: Straight-line distance from the donor to the hospital.
        my_pledge_id: The donor's active pledge for this request, if they have one.
    """

    id: UUID
    recipient_group: BloodGroup
    component_code: str
    component_name: str
    urgency: RequestUrgency
    deadline: datetime
    notes: str | None
    units_remaining: int
    distance_km: float
    hospital: HospitalSummary
    my_pledge_id: UUID | None


class OpenRequestsForDonor(BaseModel):
    """The open requests a donor can answer, and the radius searched."""

    items: list[OpenRequestForDonor]
    radius_km: float
