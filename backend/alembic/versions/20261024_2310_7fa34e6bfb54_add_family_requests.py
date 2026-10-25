"""add family requests

Adds the appeals a patient's family sends to a verified hospital from the public page. An
appeal alerts nobody: it waits until the hospital's staff confirm the patient and approve
it, which raises an ordinary blood request (linked here), or decline it with a reason.

Revision ID: 7fa34e6bfb54
Revises: fe89ae0adf5d
Create Date: 2026-10-24 23:10:41.461016+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7fa34e6bfb54"
down_revision: str | None = "fe89ae0adf5d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BLOOD_GROUPS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")
_STATUSES = ("pending", "approved", "declined")


def upgrade() -> None:
    op.create_table(
        "family_requests",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hospital_id", sa.Uuid(), nullable=False),
        sa.Column("requester_name", sa.String(length=100), nullable=False),
        sa.Column("requester_phone", sa.String(length=32), nullable=False),
        sa.Column(
            "recipient_group",
            sa.Enum(
                *_BLOOD_GROUPS,
                name="family_recipient_group",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("component_type_id", sa.Uuid(), nullable=False),
        sa.Column("units_needed", sa.Integer(), nullable=False),
        sa.Column("ward_reference", sa.String(length=200), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                *_STATUSES,
                name="family_request_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decline_reason", sa.String(length=500), nullable=True),
        sa.Column("blood_request_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "units_needed > 0", name=op.f("ck_family_requests_units_needed_positive")
        ),
        sa.ForeignKeyConstraint(
            ["blood_request_id"],
            ["blood_requests.id"],
            name=op.f("fk_family_requests_blood_request_id_blood_requests"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["component_type_id"],
            ["component_types.id"],
            name=op.f("fk_family_requests_component_type_id_component_types"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by"],
            ["users.id"],
            name=op.f("fk_family_requests_decided_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["hospital_id"],
            ["hospitals.id"],
            name=op.f("fk_family_requests_hospital_id_hospitals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_family_requests")),
    )
    op.create_index(
        "ix_family_requests_hospital_id_status",
        "family_requests",
        ["hospital_id", "status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_family_requests_requester_phone"),
        "family_requests",
        ["requester_phone"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_family_requests_requester_phone"), table_name="family_requests")
    op.drop_index("ix_family_requests_hospital_id_status", table_name="family_requests")
    op.drop_table("family_requests")
