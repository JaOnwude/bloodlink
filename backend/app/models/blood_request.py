"""Urgent blood requests raised by verified hospitals."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column_type
from app.models.enums import BloodGroup, RequestStatus, RequestUrgency


class BloodRequest(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """A hospital's appeal for a number of units of a specific blood group and component.

    Lifecycle: ``OPEN`` -> ``FULFILLED`` -> ``CLOSED``, or ``OPEN`` -> ``EXPIRED`` when the
    deadline passes first. A request becomes ``FULFILLED`` at the instant the final unit
    is pledged; the pledge service enforces that atomically under a row lock.

    The search origin for donor matching is the issuing hospital's coordinates, so the
    request carries no location of its own.

    Attributes:
        hospital_id: The facility that needs the blood.
        created_by: The staff member who raised the request.
        recipient_group: Blood group of the patient. Compatible donor groups are derived
            from the ``blood_compatibility`` table.
        component_type_id: Which component is required (whole blood, platelets, ...).
        units_needed: Number of units still required, at least one.
        urgency: Priority shown to donors and used to order alerts.
        deadline: Moment after which the request stops accepting pledges.
        notes: Optional free-text context for donors (ward, contact desk, and so on).
        status: Current lifecycle state.
        fulfilled_at: When the final required unit was pledged.
    """

    __tablename__ = "blood_requests"
    __table_args__ = (
        CheckConstraint("units_needed > 0", name="units_positive"),
        # Supports the donor-facing list of open requests ordered by deadline.
        Index("ix_blood_requests_status_deadline", "status", "deadline"),
        # Supports a hospital's own dashboard filtered by lifecycle state.
        Index("ix_blood_requests_hospital_id_status", "hospital_id", "status"),
    )

    hospital_id: UUID = Field(foreign_key="hospitals.id", ondelete="RESTRICT")
    created_by: UUID = Field(foreign_key="users.id", ondelete="RESTRICT")
    recipient_group: BloodGroup = Field(
        sa_type=enum_column_type(BloodGroup, "recipient_group")
    )
    component_type_id: UUID = Field(foreign_key="component_types.id", ondelete="RESTRICT")
    units_needed: int
    urgency: RequestUrgency = Field(sa_type=enum_column_type(RequestUrgency, "urgency"))
    deadline: datetime = Field(sa_type=DateTime(timezone=True))
    notes: str | None = Field(default=None, max_length=1000)
    status: RequestStatus = Field(
        default=RequestStatus.OPEN,
        sa_type=enum_column_type(RequestStatus, "request_status"),
        sa_column_kwargs={"server_default": RequestStatus.OPEN.value},
    )
    fulfilled_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
