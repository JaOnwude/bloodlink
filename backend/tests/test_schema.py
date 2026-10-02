"""Structural tests of the declared database schema.

These inspect SQLAlchemy metadata, so they run without a database. They protect the
guarantees the application relies on, such as uniqueness rules that prevent duplicate
pledges and duplicate alerts.
"""

from sqlalchemy import Table, UniqueConstraint
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registers tables)
from app.models import Notification, Pledge

EXPECTED_TABLES = {
    "audit_log",
    "blood_compatibility",
    "blood_requests",
    "component_types",
    "donations",
    "donor_deferrals",
    "donors",
    "hospitals",
    "notifications",
    "pledges",
    "users",
}


def _unique_column_sets(table: Table) -> set[frozenset[str]]:
    """Return the column groups covered by unique constraints or unique indexes."""
    sets = {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    sets |= {
        frozenset(column.name for column in index.columns)
        for index in table.indexes
        if index.unique
    }
    return sets


def test_all_expected_tables_are_registered() -> None:
    """Every planned table exists in the metadata."""
    assert set(SQLModel.metadata.tables) == EXPECTED_TABLES


def test_every_table_has_a_single_uuid_style_id_primary_key() -> None:
    """Primary keys are a single column named ``id``."""
    for table in SQLModel.metadata.tables.values():
        assert [column.name for column in table.primary_key.columns] == ["id"]


def test_every_table_records_creation_time() -> None:
    """Each table carries a ``created_at`` timestamp."""
    for table in SQLModel.metadata.tables.values():
        assert "created_at" in table.columns


def test_a_donor_cannot_hold_two_pledges_for_one_request() -> None:
    """The (request, donor) pair is unique on the pledges table."""
    assert frozenset({"request_id", "donor_id"}) in _unique_column_sets(Pledge.__table__)


def test_an_alert_cannot_be_recorded_twice_for_the_same_channel() -> None:
    """The (request, donor, channel) triple is unique on the notifications table."""
    assert frozenset({"request_id", "donor_id", "channel"}) in _unique_column_sets(
        Notification.__table__
    )


def test_pledges_reference_requests_and_donors() -> None:
    """Foreign keys point at the intended parent tables."""
    table = Pledge.__table__
    request_fk = next(iter(table.c.request_id.foreign_keys))
    donor_fk = next(iter(table.c.donor_id.foreign_keys))
    assert request_fk.target_fullname == "blood_requests.id"
    assert donor_fk.target_fullname == "donors.id"


def test_user_emails_and_donor_accounts_are_unique() -> None:
    """Email addresses are unique, and each account has at most one donor profile."""
    assert frozenset({"email"}) in _unique_column_sets(SQLModel.metadata.tables["users"])
    assert frozenset({"user_id"}) in _unique_column_sets(SQLModel.metadata.tables["donors"])
