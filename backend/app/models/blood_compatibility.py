"""Red-cell compatibility rules stored as data."""

from sqlalchemy import UniqueConstraint
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, enum_column_type
from app.models.enums import BloodGroup


class BloodCompatibility(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """One permitted pairing of a recipient blood group with a donor blood group.

    The complete set of rows is the red-cell compatibility chart. Matching joins against
    this table instead of embedding the chart in conditional logic, which keeps the
    rules inspectable, testable in isolation, and changeable without touching code.

    Attributes:
        recipient_group: The group of the patient who needs blood.
        donor_group: A group from which that patient can safely receive red cells.
    """

    __tablename__ = "blood_compatibility"
    __table_args__ = (
        UniqueConstraint(
            "recipient_group", "donor_group", name="uq_blood_compatibility_recipient_donor"
        ),
    )

    recipient_group: BloodGroup = Field(
        sa_type=enum_column_type(BloodGroup, "recipient_group"), index=True
    )
    donor_group: BloodGroup = Field(sa_type=enum_column_type(BloodGroup, "donor_group"))
