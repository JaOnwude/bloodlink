"""add standby donors and screening deferrals

Adds the number of standby places to blood requests, the reason a donor was deferred at
screening to pledges, and three pledge states: standby, deferred and released.

Pledge states are stored as strings guarded by a CHECK constraint, so allowing new states
means replacing that constraint rather than altering a native enum type.

Constraint names are given in full and wrapped in ``op.f``, which tells Alembic they already
follow the naming convention, so the table prefix is not added a second time.

Revision ID: ca124c6e6791
Revises: 721715816b6e
Create Date: 2026-10-21 18:44:30.406863+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ca124c6e6791"
down_revision: str | None = "721715816b6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_PLEDGE_STATES = ("pledged", "donated", "no_show", "cancelled")
_NEW_PLEDGE_STATES = (
    "pledged",
    "standby",
    "donated",
    "no_show",
    "deferred",
    "cancelled",
    "released",
)
_DEFERRAL_REASONS = (
    "low_haemoglobin",
    "blood_pressure",
    "recent_illness",
    "medication",
    "positive_screen",
    "other",
)


def _in_list(column: str, values: Sequence[str]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


def upgrade() -> None:
    op.add_column(
        "blood_requests",
        sa.Column("standby_units", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_blood_requests_standby_units_not_negative"), "blood_requests", "standby_units >= 0"
    )

    op.add_column("pledges", sa.Column("deferral_reason", sa.String(length=32), nullable=True))
    op.create_check_constraint(
        op.f("ck_pledges_deferral_reason"),
        "pledges",
        _in_list("deferral_reason", _DEFERRAL_REASONS),
    )

    op.drop_constraint(op.f("ck_pledges_pledge_status"), "pledges", type_="check")
    op.create_check_constraint(
        op.f("ck_pledges_pledge_status"), "pledges", _in_list("status", _NEW_PLEDGE_STATES)
    )


def downgrade() -> None:
    # Map the new states onto the closest old ones, so the old constraint can be restored.
    op.execute("UPDATE pledges SET status = 'cancelled' WHERE status IN ('standby', 'released')")
    op.execute("UPDATE pledges SET status = 'no_show' WHERE status = 'deferred'")
    op.drop_constraint(op.f("ck_pledges_pledge_status"), "pledges", type_="check")
    op.create_check_constraint(
        op.f("ck_pledges_pledge_status"), "pledges", _in_list("status", _OLD_PLEDGE_STATES)
    )

    op.drop_constraint(op.f("ck_pledges_deferral_reason"), "pledges", type_="check")
    op.drop_column("pledges", "deferral_reason")
    op.drop_constraint(
        op.f("ck_blood_requests_standby_units_not_negative"), "blood_requests", type_="check"
    )
    op.drop_column("blood_requests", "standby_units")
