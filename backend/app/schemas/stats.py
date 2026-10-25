"""Response model for a hospital's performance figures."""

from datetime import datetime

from pydantic import BaseModel


class HospitalStatsRead(BaseModel):
    """A hospital's figures for requests raised in the period.

    Rates are fractions between 0 and 1, and are null when there is nothing to measure yet
    (for example no request has finished), so a new hospital is never shown a misleading
    0%. See ``app.services.stats`` for the exact definitions.
    """

    period_days: int
    since: datetime
    requests_raised: int
    requests_open: int
    requests_finished: int
    requests_fulfilled: int
    fulfilment_rate: float | None
    median_minutes_to_fulfil: float | None
    pledges_resolved: int
    no_shows: int
    no_show_rate: float | None
    units_donated: int
    donors_alerted: int


class RingCoverageRead(BaseModel):
    """Donors in one postcode ring around the hospital. See ``app.services.coverage``.

    Attributes:
        ring: ``area``, ``district``, ``lga`` or ``state``.
        prefix: The postcode segments the ring covers, for example ``FC-01`` for the LGA.
        name: The ring's place name when NIPOST gives one (the LGA and the state).
        total: Donors in the ring, counting the narrower rings inside it.
        by_group: The same donors by blood group, for example ``{"O-": 2}``.
    """

    ring: str
    prefix: str
    name: str | None
    total: int
    by_group: dict[str, int]


class CoverageRead(BaseModel):
    """The donors a hospital can reach, by postcode ring and blood group. Counts only.

    Attributes:
        postcode: The hospital's postcode; empty when it has none, and so are the rings.
        rings: One entry per ring, the hospital's own area first.
        without_postcode_nearby: Reachable donors within ``radius_km`` who gave no postcode.
        radius_km: The radius used for that count.
    """

    postcode: str | None
    rings: list[RingCoverageRead]
    without_postcode_nearby: int
    radius_km: float
