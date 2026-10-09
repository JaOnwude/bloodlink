"""Tests of text-message alerts to matched donors, against a real database.

The guarantee under test is that a donor is alerted about a request at most once, however
many times alerting runs, including at the same instant. A recording sender stands in for
the SMS provider, so these tests never send a real message.
"""

import threading
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

import app.services.notifications as notifications
from app.models import Donor, Notification, User
from app.models.enums import BloodGroup, NotificationStatus, RequestStatus
from app.services.notifications import alert_matched_donors
from app.services.sms import SmsResult
from tests.helpers import (
    API,
    make_donor_record,
    make_request_record,
    make_staff_with_hospital,
    request_payload,
    sign_in,
)

# Roughly 11 km of latitude per tenth of a degree; the test hospital is in central Lagos.
LAGOS_LAT, LAGOS_LON = 6.5244, 3.3792


class RecordingSender:
    """Accepts every message and remembers it, like a provider that never fails."""

    name = "recording"

    def __init__(self, *, fail_for: set[str] | None = None, raise_error: bool = False) -> None:
        self.sent: list[tuple[str, str]] = []
        self._fail_for = fail_for or set()
        self._raise = raise_error
        self._lock = threading.Lock()

    def send(self, to: str, text: str) -> SmsResult:
        if self._raise:
            raise RuntimeError("provider exploded")
        with self._lock:
            self.sent.append((to, text))
        if to in self._fail_for:
            return SmsResult(ok=False, error="Number is on the blocked list")
        return SmsResult(ok=True, message_id=f"msg-{len(self.sent)}")


def donor_with_phone(db_session: Session, email: str, phone: str | None, **kwargs) -> Donor:
    donor = make_donor_record(db_session, email=email, **kwargs)
    user = db_session.get(User, donor.user_id)
    user.phone = phone
    db_session.add(user)
    db_session.commit()
    return donor


def setup(db_session: Session, **request_overrides):
    staff, hospital = make_staff_with_hospital(db_session)
    request = make_request_record(db_session, hospital, staff, **request_overrides)
    return staff, hospital, request


def rows(db_session: Session, request_id: UUID) -> list[Notification]:
    db_session.expire_all()
    return db_session.exec(select(Notification).where(Notification.request_id == request_id)).all()


# ---------------------------------------------------------------------------------------
# Who is alerted
# ---------------------------------------------------------------------------------------


def test_matched_donors_with_a_phone_are_alerted_once_each(
    db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)
    donor_with_phone(db_session, "a@example.com", "+2348000000001")
    donor_with_phone(db_session, "b@example.com", "+2348000000002")
    donor_with_phone(db_session, "nophone@example.com", None)
    sender = RecordingSender()

    run = alert_matched_donors(db_session, request.id, sender=sender)

    assert run.matched == 3
    assert run.newly_alerted == 2
    assert run.sent == 2
    assert run.without_phone == 1
    assert sorted(to for to, _ in sender.sent) == ["+2348000000001", "+2348000000002"]
    saved = rows(db_session, request.id)
    assert {row.status for row in saved} == {NotificationStatus.SENT}
    assert all(row.provider_message_id and row.sent_at for row in saved)


def test_donors_who_do_not_match_are_not_alerted(db_session: Session, reference_data: None) -> None:
    _, _, request = setup(db_session, recipient_group=BloodGroup.O_NEGATIVE)
    donor_with_phone(
        db_session, "apos@example.com", "+2348000000001", blood_group=BloodGroup.A_POSITIVE
    )
    donor_with_phone(
        db_session, "far@example.com", "+2348000000002", latitude=9.0765, longitude=7.3986
    )
    donor_with_phone(db_session, "private@example.com", "+2348000000003", consent=False)
    sender = RecordingSender()

    run = alert_matched_donors(db_session, request.id, sender=sender)

    assert run.matched == 0
    assert sender.sent == []


def test_a_request_that_is_not_open_alerts_nobody(
    db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session, status=RequestStatus.CLOSED)
    donor_with_phone(db_session, "a@example.com", "+2348000000001")
    sender = RecordingSender()

    assert alert_matched_donors(db_session, request.id, sender=sender).newly_alerted == 0
    assert sender.sent == []


def test_the_message_names_the_hospital_and_need_but_no_one_personal(
    db_session: Session, reference_data: None
) -> None:
    _, hospital, request = setup(db_session)
    donor_with_phone(db_session, "a@example.com", "+2348000000001")
    sender = RecordingSender()

    alert_matched_donors(db_session, request.id, sender=sender)

    [(_, text)] = sender.sent
    assert hospital.name in text
    assert "O-" in text
    assert "WAT" in text
    assert "/donor" in text
    assert "Test Donor" not in text


# ---------------------------------------------------------------------------------------
# Never twice
# ---------------------------------------------------------------------------------------


def test_running_alerts_again_sends_nothing_new(db_session: Session, reference_data: None) -> None:
    _, _, request = setup(db_session)
    donor_with_phone(db_session, "a@example.com", "+2348000000001")
    sender = RecordingSender()

    alert_matched_donors(db_session, request.id, sender=sender)
    second = alert_matched_donors(db_session, request.id, sender=sender)

    assert second.newly_alerted == 0
    assert second.already_alerted == 1
    assert len(sender.sent) == 1
    assert len(rows(db_session, request.id)) == 1


def test_simultaneous_runs_alert_each_donor_exactly_once(
    db_engine: Engine, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)
    for number in range(5):
        donor_with_phone(db_session, f"d{number}@example.com", f"+23480000000{number:02d}")
    sender = RecordingSender()
    # Read the id here: ORM objects belong to this thread's session and must not be shared.
    request_id = request.id
    barrier = threading.Barrier(4)
    runs: list[int] = []
    errors: list[BaseException] = []

    def run() -> None:
        try:
            with Session(db_engine) as session:
                barrier.wait()
                runs.append(alert_matched_donors(session, request_id, sender=sender).newly_alerted)
        except BaseException as exc:  # Reported below, so a crashed run cannot pass silently.
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert errors == []
    assert len(runs) == 4
    # Between them the four runs claimed each donor once.
    assert sum(runs) == 5
    assert len(sender.sent) == 5
    assert len({to for to, _ in sender.sent}) == 5
    assert len(rows(db_session, request_id)) == 5


def test_a_wider_radius_alerts_only_the_donors_it_adds(
    db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)
    donor_with_phone(db_session, "near@example.com", "+2348000000001")
    # About 33 km north: outside 25 km, inside 50 km.
    donor_with_phone(db_session, "further@example.com", "+2348000000002", latitude=LAGOS_LAT + 0.3)
    sender = RecordingSender()

    alert_matched_donors(db_session, request.id, sender=sender, radius_km=25)
    wider = alert_matched_donors(db_session, request.id, sender=sender, radius_km=50)

    assert wider.newly_alerted == 1
    assert wider.already_alerted == 1
    assert [to for to, _ in sender.sent] == ["+2348000000001", "+2348000000002"]


# ---------------------------------------------------------------------------------------
# Failures are recorded and contained
# ---------------------------------------------------------------------------------------


def test_a_failed_message_is_recorded_with_the_reason(
    db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)
    donor_with_phone(db_session, "a@example.com", "+2348000000001")
    sender = RecordingSender(fail_for={"+2348000000001"})

    run = alert_matched_donors(db_session, request.id, sender=sender)

    assert run.failed == 1
    [row] = rows(db_session, request.id)
    assert row.status == NotificationStatus.FAILED
    assert row.failure_reason == "Number is on the blocked list"
    assert row.sent_at is None


def test_a_sender_that_raises_is_recorded_as_failed(
    db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)
    donor_with_phone(db_session, "a@example.com", "+2348000000001")

    run = alert_matched_donors(db_session, request.id, sender=RecordingSender(raise_error=True))

    assert run.failed == 1
    [row] = rows(db_session, request.id)
    assert row.status == NotificationStatus.FAILED
    assert "RuntimeError" in row.failure_reason


# ---------------------------------------------------------------------------------------
# Through the API
# ---------------------------------------------------------------------------------------


@pytest.fixture
def recording_sender(monkeypatch: pytest.MonkeyPatch) -> RecordingSender:
    """Route every alert sent through the API to a recording sender."""
    sender = RecordingSender()
    monkeypatch.setattr(notifications, "get_sms_sender", lambda settings=None: sender)
    return sender


def test_raising_a_request_alerts_matched_donors(
    client: TestClient,
    db_session: Session,
    reference_data: None,
    recording_sender: RecordingSender,
) -> None:
    staff, _ = make_staff_with_hospital(db_session)
    donor_with_phone(db_session, "a@example.com", "+2348000000001")
    sign_in(client, staff.email)

    response = client.post(f"{API}/requests", json=request_payload())

    assert response.status_code == 201
    # The test client runs background tasks before returning.
    assert [to for to, _ in recording_sender.sent] == ["+2348000000001"]
    summary = client.get(f"{API}/requests/{response.json()['id']}/alerts").json()
    assert summary["sent"] == 1
    assert summary["total"] == 1
    assert summary["provider"] == "console"


def test_raising_a_request_succeeds_even_if_alerting_breaks(
    client: TestClient,
    db_session: Session,
    reference_data: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    staff, _ = make_staff_with_hospital(db_session)
    donor_with_phone(db_session, "a@example.com", "+2348000000001")

    def broken(*args, **kwargs):
        raise RuntimeError("database went away")

    monkeypatch.setattr(notifications, "alert_matched_donors", broken)
    sign_in(client, staff.email)

    assert client.post(f"{API}/requests", json=request_payload()).status_code == 201


def test_staff_can_alert_again_with_a_wider_radius(
    client: TestClient,
    db_session: Session,
    reference_data: None,
    recording_sender: RecordingSender,
) -> None:
    staff, _, request = setup(db_session)
    donor_with_phone(db_session, "far@example.com", "+2348000000002", latitude=LAGOS_LAT + 0.3)
    sign_in(client, staff.email)

    narrow = client.post(f"{API}/requests/{request.id}/alerts", params={"radius_km": 25}).json()
    wide = client.post(f"{API}/requests/{request.id}/alerts", params={"radius_km": 50}).json()
    again = client.post(f"{API}/requests/{request.id}/alerts", params={"radius_km": 50}).json()

    assert narrow["newly_alerted"] == 0
    assert wide["newly_alerted"] == 1
    assert again["newly_alerted"] == 0
    assert again["already_alerted"] == 1
    assert again["totals"]["sent"] == 1


def test_alerts_cannot_be_sent_for_a_closed_request(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    staff, _, request = setup(db_session, status=RequestStatus.CLOSED)
    sign_in(client, staff.email)

    assert client.post(f"{API}/requests/{request.id}/alerts").status_code == 409


def test_another_hospital_cannot_see_or_send_alerts(
    client: TestClient, db_session: Session, reference_data: None
) -> None:
    _, _, request = setup(db_session)
    other, _ = make_staff_with_hospital(db_session, email="other@example.com", name="Other")
    sign_in(client, other.email)

    assert client.get(f"{API}/requests/{request.id}/alerts").status_code == 404
    assert client.post(f"{API}/requests/{request.id}/alerts").status_code == 404


def test_an_overdue_request_alerts_nobody(db_session: Session, reference_data: None) -> None:
    _, _, request = setup(db_session, deadline=datetime.now(UTC) - timedelta(minutes=1))
    donor_with_phone(db_session, "a@example.com", "+2348000000001")
    sender = RecordingSender()

    assert alert_matched_donors(db_session, request.id, sender=sender).newly_alerted == 0
    assert sender.sent == []
