"""Donor commitments to blood requests."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, UniqueConstraint
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column_type, utcnow
from app.models.enums import PledgeStatus


class Pledge(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """A donor's commitment to give blood for one request.

    The unique constraint on (request, donor) guarantees a donor cannot hold two pledges
    for the same request. A donor who cancels and later changes their mind reactivates
    the existing row rather than inserting a second one.

    The number of pledges that count towards a request (``PLEDGED`` and ``DONATED``) is
    what the pledge service compares against ``units_needed`` while holding a row lock on
    the request, so two donors accepting simultaneously cannot exceed the units required.

    Attributes:
        request_id: The request being answered.
        donor_id: The donor making the commitment.
        status: Current state of the commitment.
        pledged_at: When the donor accepted.
        resolved_at: When staff recorded the outcome (donated or no-show).
        resolved_by: The staff member who recorded the outcome.
    """

    __tablename__ = "pledges"
    __table_args__ = (
        UniqueConstraint("request_id", "donor_id", name="uq_pledges_request_id_donor_id"),
        # Supports counting the pledges that consume a request's units.
        Index("ix_pledges_request_id_status", "request_id", "status"),
    )

    request_id: UUID = Field(foreign_key="blood_requests.id", ondelete="RESTRICT")
    donor_id: UUID = Field(foreign_key="donors.id", index=True, ondelete="RESTRICT")
    status: PledgeStatus = Field(
        default=PledgeStatus.PLEDGED,
        sa_type=enum_column_type(PledgeStatus, "pledge_status"),
        sa_column_kwargs={"server_default": PledgeStatus.PLEDGED.value},
    )
    pledged_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
    resolved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    resolved_by: UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
