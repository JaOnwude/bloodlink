"""Performance figures for one hospital: how well its requests are being answered.

These are the numbers a hospital would pay for: how often a request gets every unit it
asks for, how quickly, and how reliable the donors who pledge turn out to be. They are
worked out from the requests raised in a recent period, so a hospital can see whether
things are improving.

Definitions, kept simple enough to explain on a whiteboard:

* **Fulfilment rate:** of the requests that are finished (fulfilled, closed or expired),
  the share that reached every unit. A request that was fulfilled and later closed still
  counts as met, because it carries a ``fulfilled_at`` time. Open requests are left out:
  their outcome is not known yet. None when no request has finished.
* **Median time to fulfil:** for requests that reached every unit, the time from raising
  the request to the moment the last unit was pledged. The median is used rather than the
  mean so one unusually slow request does not distort it. None when none was fulfilled.
* **No-show rate:** of the pledges whose outcome has been recorded (donated or did not
  attend), the share where the donor did not come. None when no outcome is recorded.

Overdue requests are expired first, so the figures never count a stale ``open`` request.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import BloodRequest, Donation, Notification, Pledge
from app.models.base import utcnow
from app.models.enums import NotificationStatus, PledgeStatus, RequestStatus
from app.services.requests import expire_overdue

_FINISHED = (RequestStatus.FULFILLED, RequestStatus.CLOSED, RequestStatus.EXPIRED)


@dataclass(frozen=True)
class HospitalStats:
    """A hospital's figures for one period. Rates are fractions between 0 and 1."""

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


def hospital_stats(
    session: Session, hospital_id: UUID, *, days: int, now: datetime | None = None
) -> HospitalStats:
    """Work out the hospital's figures for requests raised in the last ``days`` days.

    Args:
        session: An open database session.
        hospital_id: The hospital to report on.
        days: How far back to look, counted from ``now``.
        now: The end of the period; defaults to the current time.
    """
    moment = now or utcnow()
    expire_overdue(session, hospital_id=hospital_id, now=moment)
    since = moment - timedelta(days=days)

    requests = session.exec(
        select(BloodRequest).where(
            BloodRequest.hospital_id == hospital_id,
            col(BloodRequest.created_at) >= since,
        )
    ).all()
    request_ids = [request.id for request in requests]

    finished = [request for request in requests if request.status in _FINISHED]
    fulfilled = [request for request in finished if request.fulfilled_at is not None]
    minutes = [
        (request.fulfilled_at - request.created_at).total_seconds() / 60
        for request in fulfilled
        if request.fulfilled_at is not None
    ]

    outcomes: dict[PledgeStatus, int] = {}
    units_donated = 0
    donors_alerted = 0
    if request_ids:
        outcomes = dict(
            session.exec(
                select(Pledge.status, func.count())
                .where(
                    col(Pledge.request_id).in_(request_ids),
                    col(Pledge.status).in_((PledgeStatus.DONATED, PledgeStatus.NO_SHOW)),
                )
                .group_by(Pledge.status)
            ).all()
        )
        units_donated = session.exec(
            select(func.coalesce(func.sum(Donation.units), 0))
            .join(Pledge, col(Pledge.id) == col(Donation.pledge_id))
            .where(col(Pledge.request_id).in_(request_ids))
        ).one()
        donors_alerted = session.exec(
            select(func.count(func.distinct(Notification.donor_id))).where(
                col(Notification.request_id).in_(request_ids),
                Notification.status == NotificationStatus.SENT,
            )
        ).one()

    no_shows = outcomes.get(PledgeStatus.NO_SHOW, 0)
    resolved = no_shows + outcomes.get(PledgeStatus.DONATED, 0)

    return HospitalStats(
        period_days=days,
        since=since,
        requests_raised=len(requests),
        requests_open=sum(1 for request in requests if request.status == RequestStatus.OPEN),
        requests_finished=len(finished),
        requests_fulfilled=len(fulfilled),
        fulfilment_rate=len(fulfilled) / len(finished) if finished else None,
        median_minutes_to_fulfil=median(minutes) if minutes else None,
        pledges_resolved=resolved,
        no_shows=no_shows,
        no_show_rate=no_shows / resolved if resolved else None,
        units_donated=int(units_donated),
        donors_alerted=int(donors_alerted),
    )
