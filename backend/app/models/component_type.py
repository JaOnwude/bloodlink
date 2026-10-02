"""Blood components and their donation rules."""

from sqlalchemy import CheckConstraint, true
from sqlmodel import Field

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ComponentType(UUIDPrimaryKeyMixin, TimestampMixin, table=True):
    """A donatable blood component together with its minimum donation interval.

    Different components recover at different rates, so the waiting period between
    donations depends on what is being given. Storing the rules as data means they can be
    reviewed and corrected by an administrator without changing or redeploying code, and
    new components can be introduced by inserting a row.

    The code is a free-form string rather than an enumeration for the same reason.

    Attributes:
        code: Stable machine identifier such as ``whole_blood``.
        name: Human-readable label.
        min_interval_days_male: Minimum days between donations for male donors.
        min_interval_days_female: Minimum days between donations for female donors.
        is_active: Inactive components remain for history but cannot be requested.
    """

    __tablename__ = "component_types"
    __table_args__ = (
        CheckConstraint("min_interval_days_male > 0", name="male_interval_positive"),
        CheckConstraint("min_interval_days_female > 0", name="female_interval_positive"),
    )

    code: str = Field(max_length=50, unique=True, index=True)
    name: str = Field(max_length=100)
    min_interval_days_male: int
    min_interval_days_female: int
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": true()})
