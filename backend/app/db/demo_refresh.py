"""Bring an existing demonstration database up to date, without starting it again.

``seed_demo_data`` runs once: on a database that already has the demonstration, it changes
nothing. A demonstration seeded before a feature existed therefore lacks that feature's
data, and its requests expire as the days pass. This fills the gaps in place:

* **Donors.** Every standard demonstration donor whose account is missing (a demonstration
  loaded by an older, smaller seed, for example) is created exactly as the seed creates it,
  with the shared demonstration password. Accounts that exist are matched by email and left
  alone, so nobody is duplicated.

* **Postcodes.** The Abuja hospital gets its sample NIPOST postcode and the Abuja donors
  their sample postcode areas, exactly as a fresh seed would give them. Records that
  already have one keep it.
* **A live request.** If the Abuja hospital has no request open for at least another day,
  a fresh O+ request is raised through the same service the API uses, so its limits and
  audit trail apply. Overdue requests are expired on the way, as they would be on any
  request. No donor is texted: alerts go out when a request is raised through the
  application, as in a recorded demonstration.
* **A phone to receive alerts.** With a phone number given (normally the developer's own,
  ``DEMO_DONOR_PHONE``), the donor who comes first for that request (nearest postcode ring,
  then distance) gets it, so the text-message alert can be seen end to end. Without one, no
  phone number changes.
* **A new shared password,** on request. ``DEMO_PASSWORD`` is only read when the accounts
  are first created, so changing it later does not reach existing accounts. Given a new
  password, every demonstration account is switched to it, for example after the old one
  was published.

Only demonstration records (accounts on the reserved ``bloodlink.example`` domain and
their hospitals) are read or changed. Running it twice changes nothing the second time.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.security import hash_password
from app.data.postcode_samples import SAMPLE_BUILDINGS
from app.db.demo_seed import (
    ADMIN_EMAIL,
    DEMO_DOMAIN,
    _create_donors,
    staff_email,
    standard_donor_emails,
)
from app.models import BloodRequest, Donor, Hospital, User
from app.models.enums import BloodGroup, RequestStatus, RequestUrgency
from app.schemas.request import RequestCreate
from app.services.matching import find_matches
from app.services.requests import create_request, expire_overdue

# A request is "live enough" for a demonstration when it stays open at least this long.
_MIN_TIME_LEFT = timedelta(days=1)

# The request raised when none is live: open for three days, so a recording can be retaken.
_REQUEST_HOURS = 72


class DemoNotSeededError(Exception):
    """Raised when there is no demonstration to refresh: run the demonstration seed first."""


class PasswordNeededError(Exception):
    """Raised when donor accounts must be created but no password was given for them."""


@dataclass(frozen=True)
class RefreshSummary:
    """What a refresh changed.

    Attributes:
        hospital_postcodes: Demonstration hospitals given a postcode.
        donor_postcodes: Demonstration donors given a postcode area.
        request_raised: True when a fresh request was raised.
        expired: Overdue requests moved to expired on the way.
        phone_donor: Email of the donor given the phone number, if one was.
        passwords_reset: Demonstration accounts switched to the new password.
        donors_created: Standard demonstration donors created because they were missing.
    """

    hospital_postcodes: int
    donor_postcodes: int
    request_raised: bool
    expired: int
    phone_donor: str | None
    passwords_reset: int = 0
    donors_created: int = 0


def _abuja_staff(session: Session) -> tuple[User, Hospital]:
    staff = session.exec(select(User).where(User.email == staff_email("abuja"))).first()
    hospital = session.get(Hospital, staff.hospital_id) if staff and staff.hospital_id else None
    if staff is None or hospital is None:
        raise DemoNotSeededError("The demonstration data is not present.")
    return staff, hospital


def _abuja_donors(session: Session) -> list[Donor]:
    """The Abuja demonstration donors, in the order they were created."""
    return list(
        session.exec(
            select(Donor)
            .join(User, col(User.id) == col(Donor.user_id))
            .where(col(User.email).endswith(f"@{DEMO_DOMAIN}"), Donor.city == "Abuja")
            .order_by(col(User.email))
        ).all()
    )


def _live_request(session: Session, hospital: Hospital) -> BloodRequest | None:
    return session.exec(
        select(BloodRequest).where(
            BloodRequest.hospital_id == hospital.id,
            BloodRequest.status == RequestStatus.OPEN,
            col(BloodRequest.deadline) > datetime.now(UTC) + _MIN_TIME_LEFT,
        )
    ).first()


def _missing_donor_accounts(session: Session) -> int:
    """How many standard demonstration donor accounts do not exist yet."""
    emails = standard_donor_emails()
    existing = session.exec(
        select(func.count()).select_from(User).where(col(User.email).in_(emails))
    ).one()
    return len(emails) - existing


def refresh_demo_data(
    session: Session,
    *,
    donor_phone: str | None = None,
    new_password: str | None = None,
    account_password: str | None = None,
) -> RefreshSummary:
    """Fill in postcodes, raise a live request, place the phone and, if given, reset the
    demonstration accounts' password. See the module notes.

    Args:
        donor_phone: Number to give the donor who comes first for the live request.
        new_password: Password to move every demonstration account to.
        account_password: Password for donor accounts created because none exist. Defaults
            to ``new_password``.

    Passwords must already have passed the password policy; the caller checks them.

    Raises:
        DemoNotSeededError: If the demonstration has not been loaded.
        PasswordNeededError: If donors must be created and no password was given.

    Raises:
        DemoNotSeededError: If the demonstration data has not been loaded.
    """
    staff, hospital = _abuja_staff(session)
    admin = session.exec(select(User).where(User.email == ADMIN_EMAIL)).first()
    if admin is None:
        raise DemoNotSeededError("The demonstration administrator is missing.")

    donors_created = 0
    if _missing_donor_accounts(session) > 0:
        password = account_password or new_password
        if not password:
            raise PasswordNeededError("Donor accounts must be created; give DEMO_PASSWORD.")
        created = _create_donors(
            session,
            admin,
            password,
            donor_phone=None,
            today=datetime.now(UTC).date(),
            skip_existing=True,
        )
        donors_created = len(created)

    hospital_postcodes = 0
    if hospital.postcode is None:
        hospital.postcode = SAMPLE_BUILDINGS[0].postcode
        session.add(hospital)
        hospital_postcodes = 1

    donor_postcodes = 0
    for index, donor in enumerate(_abuja_donors(session)):
        if donor.postcode_area is None:
            # The same spread across the five sample areas as a fresh seed.
            postcode = SAMPLE_BUILDINGS[index % len(SAMPLE_BUILDINGS)].postcode
            donor.postcode_area = postcode.rsplit("-", 1)[0]
            session.add(donor)
            donor_postcodes += 1
    session.commit()

    expired = expire_overdue(session, hospital_id=hospital.id)
    request = _live_request(session, hospital)
    request_raised = request is None
    if request is None:
        request = create_request(
            session,
            staff,
            hospital,
            RequestCreate(
                recipient_group=BloodGroup.O_POSITIVE,
                component_code="whole_blood",
                units_needed=2,
                standby_units=1,
                urgency=RequestUrgency.URGENT,
                deadline=datetime.now(UTC) + timedelta(hours=_REQUEST_HOURS),
                notes="Maternity ward. Report to the blood bank desk.",
            ),
            ip_address=None,
        )

    phone_donor = None
    if donor_phone:
        matches, _ = find_matches(session, request, hospital, radius_km=25, limit=1)
        if matches:
            donor = matches[0].donor
            user = session.get(User, donor.user_id)
            assert user is not None
            if user.phone != donor_phone:
                user.phone = donor_phone
                session.add(user)
                session.commit()
            phone_donor = user.email

    passwords_reset = 0
    if new_password:
        password_hash = hash_password(new_password)
        for user in session.exec(
            select(User).where(col(User.email).endswith(f"@{DEMO_DOMAIN}"))
        ).all():
            user.password_hash = password_hash
            session.add(user)
            passwords_reset += 1
        session.commit()

    return RefreshSummary(
        passwords_reset=passwords_reset,
        donors_created=donors_created,
        hospital_postcodes=hospital_postcodes,
        donor_postcodes=donor_postcodes,
        request_raised=request_raised,
        expired=expired,
        phone_donor=phone_donor,
    )
