"""Temporary or permanent donor ineligibility."""

from datetime import date
from uuid import UUID

from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin


class DonorDeferral(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    """A recorded reason why a donor must not currently be matched.

    Deferrals cover situations such as recent illness, surgery or travel. They are
    separate from the interval rule: a donor can be past the waiting period yet still
    deferred. The eligibility module treats any deferral that has not yet expired as
    disqualifying.

    Records are kept as history. The only permitted edit is shortening ``deferred_until``
    to end a deferral early, so no ``updated_at`` column is carried; any such change is
    captured in the audit log together with who made it.

    Attributes:
        donor_id: The deferred donor.
        reason: Brief explanation recorded by the clinician or administrator.
        deferred_until: Last day of the deferral. Null means the deferral is permanent.
        recorded_by: The staff member or administrator who recorded it.
    """

    __tablename__ = "donor_deferrals"

    donor_id: UUID = Field(foreign_key="donors.id", index=True, ondelete="CASCADE")
    reason: str = Field(max_length=500)
    deferred_until: date | None = Field(default=None)
    recorded_by: UUID = Field(foreign_key="users.id", ondelete="RESTRICT")
