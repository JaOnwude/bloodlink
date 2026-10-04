"""Log of alerts sent to donors."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column_type
from app.models.enums import NotificationChannel, NotificationStatus


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """Record that a donor was (or is about to be) alerted about a request.

    The unique constraint on (request, donor, channel) is what makes alerting idempotent:
    the sender first inserts the row and only transmits if that insert succeeds, so
    running the matching job twice, or retrying after a crash, can never produce a
    duplicate message to the same donor.

    Attributes:
        request_id: The request the alert is about.
        donor_id: The recipient.
        channel: Delivery channel used.
        status: Whether the message is queued, delivered to the provider, or failed.
        provider_message_id: Identifier returned by the messaging provider, for tracing.
        sent_at: When the provider accepted the message.
        failure_reason: Provider error text when delivery failed.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "request_id", "donor_id", "channel", name="uq_notifications_request_donor_channel"
        ),
    )

    request_id: UUID = Field(foreign_key="blood_requests.id", index=True, ondelete="CASCADE")
    donor_id: UUID = Field(foreign_key="donors.id", index=True, ondelete="CASCADE")
    channel: NotificationChannel = Field(
        default=NotificationChannel.SMS,
        sa_type=enum_column_type(NotificationChannel, "notification_channel"),
    )
    status: NotificationStatus = Field(
        default=NotificationStatus.QUEUED,
        sa_type=enum_column_type(NotificationStatus, "notification_status"),
        sa_column_kwargs={"server_default": NotificationStatus.QUEUED.value},
    )
    provider_message_id: str | None = Field(default=None, max_length=100)
    sent_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    failure_reason: str | None = Field(default=None, max_length=500)
