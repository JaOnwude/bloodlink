"""Confirmed donation history."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Donation(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """A donation that hospital staff have confirmed actually took place.

    A pledge is an intention; a donation is a verified fact. Keeping them apart provides
    a trustworthy history for eligibility, reporting and recognition, and lets a pledge
    be corrected without rewriting the record of what was given.

    A row is created in the same transaction that marks the pledge as donated and updates
    the donor's cached ``last_donation_date``.

    Attributes:
        pledge_id: The pledge this donation fulfils. Each pledge yields at most one.
        donor_id: Who donated.
        hospital_id: Where the donation was received.
        component_type_id: What was donated.
        units: Number of units collected.
        donated_at: When the donation took place.
        confirmed_by: The staff member who confirmed it.
    """

    __tablename__ = "donations"
    __table_args__ = (CheckConstraint("units > 0", name="units_positive"),)

    pledge_id: UUID = Field(foreign_key="pledges.id", unique=True, ondelete="RESTRICT")
    donor_id: UUID = Field(foreign_key="donors.id", index=True, ondelete="RESTRICT")
    hospital_id: UUID = Field(foreign_key="hospitals.id", index=True, ondelete="RESTRICT")
    component_type_id: UUID = Field(foreign_key="component_types.id", ondelete="RESTRICT")
    units: int = Field(default=1)
    donated_at: datetime = Field(sa_type=DateTime(timezone=True))
    confirmed_by: UUID = Field(foreign_key="users.id", ondelete="RESTRICT")
