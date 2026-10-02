"""Append-only record of sensitive actions."""

from typing import Any
from uuid import UUID

from sqlalchemy import Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class AuditLog(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    """An immutable entry describing who did what to which record, and when.

    Audit entries are written for hospital verification decisions, request lifecycle
    changes, pledge resolutions and account deactivations. Application code only ever
    inserts into this table; it never updates or deletes rows, so the trail can be relied
    upon when a decision is questioned.

    Attributes:
        actor_user_id: The user who performed the action. Null for system actions such as
            automatic request expiry, and preserved as null if the user is later removed.
        action: Dotted verb describing the event, for example ``hospital.verified``.
        entity_type: Kind of record affected, for example ``hospital``.
        entity_id: Identifier of the affected record.
        before: Snapshot of the relevant fields before the change, when applicable.
        after: Snapshot of the relevant fields after the change, when applicable.
        ip_address: Network address of the caller, for security investigations.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_log_created_at", "created_at"),
    )

    actor_user_id: UUID | None = Field(
        default=None, foreign_key="users.id", index=True, ondelete="SET NULL"
    )
    action: str = Field(max_length=100, index=True)
    entity_type: str = Field(max_length=100)
    entity_id: UUID | None = Field(default=None)
    before: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    after: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    ip_address: str | None = Field(default=None, max_length=64)
