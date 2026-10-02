"""Hospitals and blood banks that raise blood requests."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column_type
from app.models.enums import VerificationStatus


class Hospital(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """A healthcare facility registered on the platform.

    A hospital starts in the ``PENDING`` state and cannot raise requests until an
    administrator verifies it. Requiring verification protects donors from fraudulent
    appeals and is the foundation of the platform's trust model.

    The identity of the reviewing administrator is intentionally not stored on this row.
    It is captured in the append-only ``audit_log`` together with the decision, which
    keeps a full history if a hospital is rejected and later re-reviewed.

    Attributes:
        name: Official facility name.
        address: Street address.
        city: City or town, used for display and coarse filtering.
        state: Nigerian state (or equivalent administrative region).
        latitude: WGS84 latitude of the facility, used as the origin for donor searches.
        longitude: WGS84 longitude of the facility.
        registration_number: Regulator-issued registration or licence number.
        contact_phone: Switchboard or blood bank desk number.
        verification_status: Current state of the administrative review.
        verified_at: When the hospital was last verified, if it has been.
        rejection_reason: Explanation shown to the hospital when a registration is rejected.
    """

    __tablename__ = "hospitals"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="longitude_range"),
    )

    name: str = Field(max_length=200, index=True)
    address: str = Field(max_length=500)
    city: str = Field(max_length=100, index=True)
    state: str = Field(max_length=100)
    latitude: float
    longitude: float
    registration_number: str | None = Field(default=None, max_length=100)
    contact_phone: str = Field(max_length=32)
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.PENDING,
        sa_type=enum_column_type(VerificationStatus, "verification_status"),
        sa_column_kwargs={"server_default": VerificationStatus.PENDING.value},
        index=True,
    )
    verified_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    rejection_reason: str | None = Field(default=None, max_length=500)
