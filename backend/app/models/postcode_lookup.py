"""Cached answers from paid NIPOST postcode lookups."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.base import CreatedAtMixin, UUIDPrimaryKeyMixin, utcnow


class PostcodeLookup(UUIDPrimaryKeyMixin, CreatedAtMixin, table=True):
    """The most detailed answer NIPOST has given for one postcode.

    Lookups from level 2 upwards cost credits. A building's address and use change rarely,
    so each answer is kept and reused: BloodLink pays for a building once, not every time
    someone registers there or an administrator reviews it.

    Answers are kept per source, so sandbox answers are never served once the live key is
    in use.

    Attributes:
        source: Which dataset answered: ``test`` (the NIPOST sandbox) or ``live``.
        postcode: The postcode in its dashed form.
        level: The lookup level the stored answer was fetched at.
        payload: The answer as NIPOST returned it, inside the ``data`` envelope.
        fetched_at: When NIPOST was last asked. Later than ``created_at`` once a building
            has been looked up again at a higher level.
    """

    __tablename__ = "postcode_lookups"
    __table_args__ = (UniqueConstraint("source", "postcode"),)

    source: str = Field(max_length=8)
    postcode: str = Field(max_length=15)
    level: int
    payload: dict[str, Any] = Field(sa_type=JSONB)
    fetched_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
