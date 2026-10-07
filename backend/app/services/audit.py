"""Writing entries to the audit log."""

from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.models import AuditLog, User


def record_audit(
    session: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Add an audit entry to the session without committing it.

    The entry is deliberately not committed here. The caller commits it together with the
    change it describes, so either both are saved or neither is, and the log can never
    claim something happened that was rolled back (or miss something that was kept).

    Args:
        actor: The user who performed the action, or None for actions taken by the system.
        action: Dotted verb describing the event, for example ``hospital.verified``.
        entity_type: Kind of record affected, for example ``hospital``.
        entity_id: Identifier of the affected record.
        before: JSON-serialisable snapshot of the relevant fields before the change.
        after: JSON-serialisable snapshot of the relevant fields after the change.
        ip_address: Network address of the caller.
    """
    entry = AuditLog(
        actor_user_id=actor.id if actor is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        ip_address=ip_address,
    )
    session.add(entry)
    return entry
