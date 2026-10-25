"""Appeals for blood made by a patient's family, waiting for the hospital to confirm them."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column_type
from app.models.enums import BloodGroup, FamilyRequestStatus


class FamilyRequest(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """A family's appeal to a verified hospital to find donors for their patient.

    In Nigeria the search for blood often falls on the family: a doctor writes down the
    group and units, and relatives are sent to find donors. BloodLink lets them ask from a
    public page, without an account, but the appeal never reaches a donor directly. It goes
    to the hospital named, whose staff confirm the patient is on their ward before raising a
    real blood request from it. Donors are therefore only ever alerted by a verified
    hospital, and a fake appeal stops at the hospital desk.

    The family's name and phone number are shown only to that hospital's staff, so they can
    call back. The id doubles as the family's private tracking link.

    Attributes:
        hospital_id: The verified hospital the appeal is sent to.
        requester_name: Who is asking, so the hospital knows whom to call.
        requester_phone: Where the hospital can reach them.
        recipient_group: The patient's blood group, as the family was told it.
        component_type_id: What the doctor asked for, such as whole blood.
        units_needed: How many units the doctor asked for.
        ward_reference: The ward, bed or lab slip number, so staff can find the patient.
        notes: Anything else the family wants the hospital to know.
        status: Pending, approved or declined.
        decided_by: The staff member who approved or declined it.
        decided_at: When they did.
        decline_reason: Why it was declined, shown to the family.
        blood_request_id: The blood request raised from it, once approved.
    """

    __tablename__ = "family_requests"
    __table_args__ = (
        CheckConstraint("units_needed > 0", name="units_needed_positive"),
        Index("ix_family_requests_hospital_id_status", "hospital_id", "status"),
    )

    hospital_id: UUID = Field(foreign_key="hospitals.id", ondelete="CASCADE")
    requester_name: str = Field(max_length=100)
    requester_phone: str = Field(max_length=32, index=True)
    recipient_group: BloodGroup = Field(
        sa_type=enum_column_type(BloodGroup, "family_recipient_group")
    )
    component_type_id: UUID = Field(foreign_key="component_types.id", ondelete="RESTRICT")
    units_needed: int
    ward_reference: str = Field(max_length=200)
    notes: str | None = Field(default=None, max_length=500)
    status: FamilyRequestStatus = Field(
        default=FamilyRequestStatus.PENDING,
        sa_type=enum_column_type(FamilyRequestStatus, "family_request_status"),
        sa_column_kwargs={"server_default": FamilyRequestStatus.PENDING.value},
    )
    decided_by: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    decided_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    decline_reason: str | None = Field(default=None, max_length=500)
    blood_request_id: UUID | None = Field(
        default=None, foreign_key="blood_requests.id", ondelete="SET NULL"
    )
