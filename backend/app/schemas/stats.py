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
