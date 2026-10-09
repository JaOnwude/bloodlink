"""Alerting matched donors about a blood request, never twice.

When a hospital raises a request, the donors it matches are sent a short text message. The
same donors are what staff see on the request page, because the list comes from the same
matching service: compatible, eligible, available, agreed to be contacted, nearby.

**No duplicates.** The ``notifications`` table has a unique constraint on (request, donor,
channel). Before sending, the service inserts the donor's row with ``ON CONFLICT DO
NOTHING`` and commits. Only the run whose insert succeeded goes on to send; any other run,
whether a retry, a second click or a parallel worker, finds the row already there and
skips that donor. The decision to send and the record of it are therefore one atomic step.

The trade-off is deliberate: if the process stops between recording a row and sending,
that donor is left ``queued`` and is not retried automatically, because nobody can tell
whether the provider accepted the message. Missing one alert is safer than texting a donor
twice at night about the same emergency.

**Failures do not spread.** A failed message is recorded with the provider's reason, and
raising the request still succeeds.

Messages carry no patient details and no donor names: only the hospital, what is needed,
by when, and a link to sign in and respond.
"""

import logging
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.models import BloodRequest, ComponentType, Donor, Hospital, Notification, User
from app.models.base import utcnow
from app.models.enums import NotificationChannel, NotificationStatus, RequestStatus
from app.services.matching import find_matches
from app.services.sms import SmsSender, get_sms_sender

logger = logging.getLogger("bloodlink.alerts")

# West Africa Time. Nigeria does not observe daylight saving, so a fixed offset is exact
# and avoids depending on the time zone database, which Windows does not ship.
WAT = timezone(timedelta(hours=1), "WAT")


@dataclass(frozen=True)
class AlertRun:
    """What one alerting run did.

    Attributes:
        matched: Donors who match the request within the radius (capped by the settings).
        newly_alerted: Donors messaged for the first time in this run.
        sent: Of those, how many the provider accepted.
        failed: Of those, how many failed.
        already_alerted: Donors skipped because an earlier run already messaged them.
        without_phone: Donors skipped because they have not given a phone number.
    """

    matched: int = 0
    newly_alerted: int = 0
    sent: int = 0
    failed: int = 0
    already_alerted: int = 0
    without_phone: int = 0


def compose_alert(
    request: BloodRequest, hospital: Hospital, component: ComponentType, distance_km: float
) -> str:
    """The text a donor receives. Kept short, so it fits in very few message parts."""
    deadline = request.deadline.astimezone(WAT).strftime("%d %b %H:%M")
    urgency = request.urgency.value.upper()
    link = f"{get_settings().frontend_url.rstrip('/')}/donor"
    return (
        f"BloodLink {urgency}: {hospital.name} ({hospital.city}, {distance_km:.0f} km) needs "
        f"{request.recipient_group.value} {component.name.lower()} by {deadline} WAT. "
        f"Can you help? Respond at {link}"
    )


def _claim(session: Session, request_id: UUID, donor_id: UUID) -> UUID | None:
    """Record that this run will alert the donor, unless another run already has.

    Returns the new row's id, or None if a row already existed. Commits immediately, so a
    competing run sees the claim at once.
    """
    statement = (
        insert(Notification)
        .values(
            # The model creates ids in Python, which a core INSERT does not run.
            id=uuid4(),
            request_id=request_id,
            donor_id=donor_id,
            channel=NotificationChannel.SMS,
            status=NotificationStatus.QUEUED,
        )
        .on_conflict_do_nothing(constraint="uq_notifications_request_donor_channel")
        .returning(col(Notification.id))
    )
    claimed = session.execute(statement).scalar_one_or_none()
    session.commit()
    return claimed


def alert_matched_donors(
    session: Session,
    request_id: UUID,
    *,
    radius_km: float | None = None,
    sender: SmsSender | None = None,
) -> AlertRun:
    """Text every matched donor who has not been alerted about this request yet.

    Safe to call any number of times, including at the same moment from several places:
    each donor is messaged at most once per request. Calling it again with a wider radius
    alerts only the donors the wider search adds.

    Args:
        session: An open database session.
        request_id: The request to alert donors about. Only an open request alerts anyone.
        radius_km: How far from the hospital to look; defaults to the configured radius.
        sender: The sender to use; defaults to the one chosen by the settings.

    Returns:
        Counts of what happened.
    """
    request = session.get(BloodRequest, request_id)
    if request is None or request.status != RequestStatus.OPEN or request.deadline <= utcnow():
        return AlertRun()
    hospital = session.get(Hospital, request.hospital_id)
    component = session.get(ComponentType, request.component_type_id)
    if hospital is None or component is None:
        return AlertRun()

    settings = get_settings()
    radius = radius_km if radius_km is not None else settings.default_search_radius_km
    matches, _ = find_matches(
        session, request, hospital, radius_km=radius, limit=settings.alert_max_donors
    )
    if not matches:
        return AlertRun()

    phones = dict(
        session.exec(
            select(Donor.id, User.phone)
            .join(User, col(User.id) == col(Donor.user_id))
            .where(col(Donor.id).in_([match.donor.id for match in matches]))
        ).all()
    )

    outbox = sender or get_sms_sender(settings)
    counts: Counter[str] = Counter()
    for match in matches:
        phone = phones.get(match.donor.id)
        if not phone:
            counts["without_phone"] += 1
            continue

        notification_id = _claim(session, request.id, match.donor.id)
        if notification_id is None:
            counts["already_alerted"] += 1
            continue
        counts["newly_alerted"] += 1

        text = compose_alert(request, hospital, component, match.distance_km)
        try:
            result = outbox.send(phone, text)
        except Exception as exc:  # A sender must not raise, but never let one stop the run.
            logger.exception("SMS sender %s raised", outbox.name)
            result_ok, message_id, error = False, None, f"Sender error ({type(exc).__name__})."
        else:
            result_ok, message_id, error = result.ok, result.message_id, result.error

        notification = session.get(Notification, notification_id)
        if notification is not None:
            notification.status = (
                NotificationStatus.SENT if result_ok else NotificationStatus.FAILED
            )
            notification.provider_message_id = message_id
            notification.failure_reason = error
            notification.sent_at = utcnow() if result_ok else None
            session.add(notification)
            session.commit()
        counts["sent" if result_ok else "failed"] += 1

    return AlertRun(
        matched=len(matches),
        newly_alerted=counts["newly_alerted"],
        sent=counts["sent"],
        failed=counts["failed"],
        already_alerted=counts["already_alerted"],
        without_phone=counts["without_phone"],
    )


def alert_in_background(engine: Engine, request_id: UUID) -> None:
    """Run ``alert_matched_donors`` in its own session, after the response has been sent.

    Used when a request is raised, so the hospital is not kept waiting for the SMS provider.
    Any error is logged and swallowed: alerting must never break raising a request.
    """
    try:
        with Session(engine) as session:
            run = alert_matched_donors(session, request_id)
        logger.info(
            "Alerts for request %s: %s new, %s sent, %s failed",
            request_id,
            run.newly_alerted,
            run.sent,
            run.failed,
        )
    except Exception:
        logger.exception("Alerting donors for request %s failed", request_id)


@dataclass(frozen=True)
class AlertCounts:
    """How many alerts about a request were sent, failed or are still queued."""

    sent: int
    failed: int
    queued: int

    @property
    def total(self) -> int:
        return self.sent + self.failed + self.queued


def count_alerts(session: Session, request_id: UUID) -> AlertCounts:
    """Count the request's alerts by delivery state."""
    statuses = Counter(
        session.exec(select(Notification.status).where(Notification.request_id == request_id)).all()
    )
    return AlertCounts(
        sent=statuses[NotificationStatus.SENT],
        failed=statuses[NotificationStatus.FAILED],
        queued=statuses[NotificationStatus.QUEUED],
    )
