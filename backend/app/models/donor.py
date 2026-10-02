"""Donor profiles."""

from datetime import date
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, false, true
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column_type
from app.models.enums import BloodGroup, Sex


class Donor(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """The donation-related profile of a user with the donor role.

    Holding this separately from ``users`` keeps health-adjacent and location data out of
    the authentication table and allows it to be access-controlled more tightly.

    Attributes:
        user_id: The owning account. One account has at most one donor profile.
        blood_group: ABO/Rh group, used with the compatibility rules to match requests.
        date_of_birth: Used to evaluate the permitted donor age range.
        weight_kg: Body weight, used to evaluate the minimum weight rule.
        sex: Used to select the applicable minimum interval between donations.
        latitude: Approximate latitude used for distance ranking.
        longitude: Approximate longitude used for distance ranking.
        city: City or town shown to hospital staff after a donor pledges.
        last_donation_date: Cached date of the most recent confirmed donation. It is
            updated in the same transaction that records the donation, so eligibility
            checks need not scan the full donation history.
        is_available: Self-service switch to pause alerts without deleting the profile.
        consent_to_contact: Explicit permission to be contacted. Donors without consent
            are never matched or notified.
    """

    __tablename__ = "donors"
    __table_args__ = (
        CheckConstraint("weight_kg > 0", name="weight_positive"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
        # Supports the matching query, which always filters on group and availability.
        Index("ix_donors_blood_group_is_available", "blood_group", "is_available"),
    )

    user_id: UUID = Field(foreign_key="users.id", unique=True, index=True, ondelete="CASCADE")
    blood_group: BloodGroup = Field(sa_type=enum_column_type(BloodGroup, "blood_group"))
    date_of_birth: date
    weight_kg: float
    sex: Sex = Field(sa_type=enum_column_type(Sex, "sex"))
    latitude: float
    longitude: float
    city: str = Field(max_length=100)
    last_donation_date: date | None = Field(default=None)
    is_available: bool = Field(default=True, sa_column_kwargs={"server_default": true()})
    consent_to_contact: bool = Field(
        default=False, sa_column_kwargs={"server_default": false()}
    )
