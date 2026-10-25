"""add postcodes and postcode lookup cache

Adds Nigeria's digital postcode to hospitals and donors, and a table that keeps paid NIPOST
lookups so each building is paid for once.

A hospital keeps its full building postcode, because it is a public place. A donor keeps
only the area part of theirs (the postcode without its building unit), so their home is
never stored. Both are optional: existing rows have none until they are next edited.

Revision ID: fe89ae0adf5d
Revises: ca124c6e6791
Create Date: 2026-10-24 22:33:12.528423+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "fe89ae0adf5d"
down_revision: str | None = "ca124c6e6791"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "postcode_lookups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=8), nullable=False),
        sa.Column("postcode", sa.String(length=15), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_postcode_lookups")),
        sa.UniqueConstraint("source", "postcode", name=op.f("uq_postcode_lookups_source_postcode")),
    )
    op.add_column("donors", sa.Column("postcode_area", sa.String(length=12), nullable=True))
    op.create_index(op.f("ix_donors_postcode_area"), "donors", ["postcode_area"], unique=False)
    op.add_column("hospitals", sa.Column("postcode", sa.String(length=15), nullable=True))
    op.create_index(op.f("ix_hospitals_postcode"), "hospitals", ["postcode"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_hospitals_postcode"), table_name="hospitals")
    op.drop_column("hospitals", "postcode")
    op.drop_index(op.f("ix_donors_postcode_area"), table_name="donors")
    op.drop_column("donors", "postcode_area")
    op.drop_table("postcode_lookups")
