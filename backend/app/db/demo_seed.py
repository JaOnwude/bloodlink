"""Demonstration data: hospitals, staff, donors, requests and pledges in three cities.

This fills an empty database with enough realistic activity to show every part of
BloodLink without typing anything in first: an administrator with hospitals waiting for
review, verified hospitals in Lagos, Abuja and Enugu with open, fulfilled and expired
requests, and donors with a spread of blood groups, some of whom have pledged or donated.

Design choices:

* **Fictional facilities.** Hospital names are invented and their phone numbers are not
  real lines, so a deployed demonstration never presents itself as a real hospital.
* **No real phone numbers for donors.** Seeded donors have no phone, so alerts can never
  reach a stranger. One donor (``donor01``) can be given a number on request, for example
  the developer's own, to try the text-message alerts end to end.
* **The real rules.** Requests, pledges and donations are created through the same
  services the API uses, so the row locks, the eligibility rules and the audit log all
  apply, and the data is exactly what the application itself would have produced.
* **Run once.** Seeding is skipped when the demonstration administrator already exists, so
  running it again changes nothing.

Every demonstration account uses an address on the reserved ``bloodlink.example`` domain
and shares one password supplied by the caller.
"""

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.db.seed import seed_reference_data
from app.models import BloodRequest, Donation, Donor, DonorDeferral, Hospital, Pledge, User
from app.models.base import utcnow
from app.models.enums import (
    BloodGroup,
    RequestStatus,
    RequestUrgency,
    Sex,
    UserRole,
    VerificationStatus,
)
from app.schemas.request import RequestCreate
from app.services.audit import record_audit
from app.services.auth import create_user
from app.services.pledges import create_pledge, resolve_pledge
from app.services.requests import create_request, expire_overdue

DEMO_DOMAIN = "bloodlink.example"
ADMIN_EMAIL = f"admin@{DEMO_DOMAIN}"

# Same seed every run, so the donors' names, ages and positions are reproducible.
_RANDOM_SEED = 2026

# City centres. Donors are scattered within a few kilometres of them.
_CITIES = {
    "Lagos": {"state": "Lagos", "latitude": 6.5244, "longitude": 3.3792},
    "Abuja": {"state": "Federal Capital Territory", "latitude": 9.0765, "longitude": 7.3986},
    "Enugu": {"state": "Enugu", "latitude": 6.4584, "longitude": 7.5464},
}


@dataclass(frozen=True)
class _HospitalSpec:
    key: str
    name: str
    address: str
    city: str
    status: VerificationStatus
    staff_name: str
    offset: tuple[float, float] = (0.0, 0.0)
    rejection_reason: str | None = None


_HOSPITALS = (
    _HospitalSpec(
        key="lagos",
        name="Lagoon Specialist Hospital",
        address="14 Marina Road, Lagos Island",
        city="Lagos",
        status=VerificationStatus.VERIFIED,
        staff_name="Funmilayo Adeyemi",
        offset=(-0.06, 0.02),
    ),
    _HospitalSpec(
        key="abuja",
        name="Unity Teaching Hospital",
        address="Plot 22 Independence Avenue, Central Business District",
        city="Abuja",
        status=VerificationStatus.VERIFIED,
        staff_name="Ibrahim Musa",
    ),
    _HospitalSpec(
        key="enugu",
        name="Coal City General Hospital",
        address="5 Okpara Avenue, Enugu",
        city="Enugu",
        status=VerificationStatus.VERIFIED,
        staff_name="Chiamaka Eze",
    ),
    _HospitalSpec(
        key="pending",
        name="Surulere Family Clinic",
        address="31 Adeniran Ogunsanya Street, Surulere",
        city="Lagos",
        status=VerificationStatus.PENDING,
        staff_name="Tunde Bakare",
        offset=(-0.02, -0.02),
    ),
    _HospitalSpec(
        key="rejected",
        name="Kubwa Community Health Centre",
        address="Kubwa Expressway, Kubwa",
        city="Abuja",
        status=VerificationStatus.REJECTED,
        staff_name="Aisha Bello",
        offset=(0.08, -0.08),
        rejection_reason=(
            "The registration number does not match our records. Please upload the "
            "licence issued by the state ministry of health."
        ),
    ),
)

# Blood groups per city, roughly following how common each group is in Nigeria (O+ most
# common, Rh-negative groups rare), with enough negatives for the O- request to be met.
_DONOR_GROUPS = {
    "Lagos": ["O-", "O+", "O+", "A+", "O+", "B+", "O-", "A+", "O+", "B+", "AB+", "A-"],
    "Abuja": ["O+", "B+", "O+", "A+", "B+", "O-", "O+", "B-"],
    "Enugu": ["O+", "O+", "A+", "B+", "O+", "O-", "AB+", "O+"],
}

_FIRST_NAMES = {
    Sex.MALE: [
        "Chinedu",
        "Emeka",
        "Tunde",
        "Segun",
        "Musa",
        "Ifeanyi",
        "Kelechi",
        "Yusuf",
        "Obinna",
        "Damilola",
        "Uche",
        "Bello",
        "Kunle",
        "Nnamdi",
    ],
    Sex.FEMALE: [
        "Ngozi",
        "Amaka",
        "Folake",
        "Aisha",
        "Zainab",
        "Chioma",
        "Bisi",
        "Halima",
        "Adaeze",
        "Yetunde",
        "Nkechi",
        "Hauwa",
        "Temitope",
        "Ifeoma",
    ],
}
_LAST_NAMES = [
    "Okafor",
    "Adeyemi",
    "Bello",
    "Nwosu",
    "Ibrahim",
    "Okeke",
    "Balogun",
    "Eze",
    "Abubakar",
    "Olawale",
    "Chukwu",
    "Danjuma",
    "Afolabi",
    "Obi",
    "Lawal",
    "Nnadi",
    "Ogunleye",
    "Usman",
]


@dataclass(frozen=True)
class DemoSummary:
    """What a seeding run did.

    Attributes:
        created: False when the demonstration data was already present and nothing changed.
    """

    created: bool
    users: int
    hospitals: int
    donors: int
    requests: int
    pledges: int
    donations: int


def staff_email(key: str) -> str:
    """The sign-in address of a demonstration hospital's staff member."""
    return f"staff.{key}@{DEMO_DOMAIN}"


def donor_email(number: int) -> str:
    """The sign-in address of a demonstration donor, numbered from 1."""
    return f"donor{number:02d}@{DEMO_DOMAIN}"


def _summary(session: Session, *, created: bool) -> DemoSummary:
    """Counts of the demonstration records currently in the database."""
    demo_users = select(User.id).where(col(User.email).endswith(f"@{DEMO_DOMAIN}"))
    hospital_ids = select(User.hospital_id).where(
        col(User.email).endswith(f"@{DEMO_DOMAIN}"), col(User.hospital_id).is_not(None)
    )
    demo_requests = select(BloodRequest.id).where(col(BloodRequest.hospital_id).in_(hospital_ids))

    def count(query) -> int:
        return session.exec(select(func.count()).select_from(query.subquery())).one()

    return DemoSummary(
        created=created,
        users=count(demo_users),
        hospitals=count(select(Hospital.id).where(col(Hospital.id).in_(hospital_ids))),
        donors=count(select(Donor.id).where(col(Donor.user_id).in_(demo_users))),
        requests=count(demo_requests),
        pledges=count(select(Pledge.id).where(col(Pledge.request_id).in_(demo_requests))),
        donations=count(select(Donation.id).where(col(Donation.hospital_id).in_(hospital_ids))),
    )


def _create_hospitals(
    session: Session, admin: User, password: str
) -> dict[str, tuple[Hospital, User]]:
    """Create each hospital with one staff member, in its review state."""
    created: dict[str, tuple[Hospital, User]] = {}
    for number, spec in enumerate(_HOSPITALS, start=1):
        city = _CITIES[spec.city]
        staff = create_user(
            session,
            email=staff_email(spec.key),
            password=password,
            full_name=spec.staff_name,
            role=UserRole.HOSPITAL_STAFF,
        )
        hospital = Hospital(
            name=spec.name,
            address=spec.address,
            city=spec.city,
            state=city["state"],
            latitude=round(city["latitude"] + spec.offset[0], 6),
            longitude=round(city["longitude"] + spec.offset[1], 6),
            registration_number=f"DEMO-{number:04d}",
            # Not a real line: a demonstration must never send anyone to call a stranger.
            contact_phone=f"+23400000000{number:02d}",
            verification_status=spec.status,
            verified_at=utcnow() if spec.status == VerificationStatus.VERIFIED else None,
            rejection_reason=spec.rejection_reason,
        )
        session.add(hospital)
        session.flush()
        staff.hospital_id = hospital.id
        session.add(staff)
        if spec.status != VerificationStatus.PENDING:
            record_audit(
                session,
                actor=admin,
                action=f"hospital.{spec.status.value}",
                entity_type="hospital",
                entity_id=hospital.id,
                after={"verification_status": spec.status.value},
            )
        session.commit()
        created[spec.key] = (hospital, staff)
    return created


def _create_donors(
    session: Session,
    admin: User,
    password: str,
    *,
    donor_phone: str | None,
    today: date,
) -> list[tuple[User, Donor]]:
    """Create the donors, city by city, with a few deliberate edge cases.

    ``donor01`` is an eligible O- donor in Lagos, the account to sign in with to try
    pledging. Among the rest are donors who gave recently, paused their alerts, did not
    agree to be contacted, or are deferred, so each matching rule has someone to exclude.
    """
    rng = random.Random(_RANDOM_SEED)
    donors: list[tuple[User, Donor]] = []
    number = 0
    for city_name, groups in _DONOR_GROUPS.items():
        city = _CITIES[city_name]
        for group in groups:
            number += 1
            sex = Sex.MALE if rng.random() < 0.55 else Sex.FEMALE
            full_name = f"{rng.choice(_FIRST_NAMES[sex])} {rng.choice(_LAST_NAMES)}"
            user = create_user(
                session,
                email=donor_email(number),
                password=password,
                full_name=full_name,
                role=UserRole.DONOR,
                phone=donor_phone if number == 1 else None,
            )
            age_days = rng.randint(19 * 365, 55 * 365)
            donor = Donor(
                user_id=user.id,
                blood_group=BloodGroup(group),
                date_of_birth=today - timedelta(days=age_days),
                weight_kg=round(rng.uniform(55, 95), 1),
                sex=sex,
                # Within roughly eight kilometres of the city centre.
                latitude=round(city["latitude"] + rng.uniform(-0.07, 0.07), 6),
                longitude=round(city["longitude"] + rng.uniform(-0.07, 0.07), 6),
                city=city_name,
                last_donation_date=(
                    today - timedelta(days=rng.randint(130, 400)) if rng.random() < 0.6 else None
                ),
                is_available=True,
                consent_to_contact=True,
            )
            session.add(donor)
            donors.append((user, donor))
    session.commit()

    # Edge cases, chosen by position so they are the same every run.
    _, gave_recently = donors[4]
    gave_recently.last_donation_date = today - timedelta(days=30)
    _, paused = donors[8]
    paused.is_available = False
    _, private = donors[9]
    private.consent_to_contact = False
    _, deferred = donors[14]
    session.add_all([gave_recently, paused, private])
    session.add(
        DonorDeferral(
            donor_id=deferred.id,
            reason="Recent malaria treatment",
            deferred_until=today + timedelta(days=21),
            recorded_by=admin.id,
        )
    )
    # donor01 is always eligible, whatever the random history gave them.
    _, first = donors[0]
    first.last_donation_date = None
    session.add(first)
    session.commit()
    for _, donor in donors:
        session.refresh(donor)
    return donors


def _raise(
    session: Session,
    hospital: Hospital,
    staff: User,
    *,
    group: str,
    units: int,
    urgency: RequestUrgency,
    hours: float,
    component: str = "whole_blood",
    notes: str | None = None,
) -> BloodRequest:
    """Raise a request through the same service the API uses."""
    return create_request(
        session,
        staff,
        hospital,
        RequestCreate(
            recipient_group=BloodGroup(group),
            component_code=component,
            units_needed=units,
            urgency=urgency,
            deadline=datetime.now(UTC) + timedelta(hours=hours),
            notes=notes,
        ),
        ip_address=None,
    )


def _pledge(session: Session, donor_pair: tuple[User, Donor], request: BloodRequest) -> Pledge:
    user, donor = donor_pair
    return create_pledge(session, user, donor, request.id, ip_address=None).pledge


def seed_demo_data(
    session: Session,
    *,
    password: str,
    donor_phone: str | None = None,
    today: date | None = None,
) -> DemoSummary:
    """Load the demonstration data, unless it is already there.

    Args:
        session: An open database session.
        password: The password every demonstration account signs in with. The caller is
            responsible for checking it against the password policy.
        donor_phone: Optional phone number for ``donor01``, to receive real test alerts.
        today: The day to build ages and donation history around; defaults to today (UTC).

    Returns:
        Counts of the demonstration records, with ``created`` False if nothing was added.
    """
    if session.exec(select(User.id).where(User.email == ADMIN_EMAIL)).first() is not None:
        return _summary(session, created=False)

    on_day = today or datetime.now(UTC).date()
    seed_reference_data(session)

    admin = create_user(
        session,
        email=ADMIN_EMAIL,
        password=password,
        full_name="Demo Administrator",
        role=UserRole.ADMIN,
    )
    hospitals = _create_hospitals(session, admin, password)
    donors = _create_donors(session, admin, password, donor_phone=donor_phone, today=on_day)

    lagos, lagos_staff = hospitals["lagos"]
    abuja, abuja_staff = hospitals["abuja"]
    enugu, enugu_staff = hospitals["enugu"]

    def eligible_in(city: str, *groups: str, skip: int = 1) -> list[tuple[User, Donor]]:
        """Donors in a city with one of the groups, leaving out donor01 by default."""
        return [
            pair
            for index, pair in enumerate(donors)
            if index >= skip and pair[1].city == city and pair[1].blood_group.value in groups
        ]

    # Lagos: an open critical O- request nobody has answered yet, for donor01 to pledge to.
    _raise(
        session,
        lagos,
        lagos_staff,
        group="O-",
        units=2,
        urgency=RequestUrgency.CRITICAL,
        hours=6,
        notes="Postpartum haemorrhage, maternity ward. Ask for the blood bank desk.",
    )

    # Lagos: an urgent A+ request part-way there, with one donor already pledged.
    a_positive = _raise(
        session,
        lagos,
        lagos_staff,
        group="A+",
        units=3,
        urgency=RequestUrgency.URGENT,
        hours=20,
        notes="Road traffic accident, theatre 2.",
    )
    lagos_a_pos_donors = eligible_in("Lagos", "A+", "A-", "O+")
    _pledge(session, lagos_a_pos_donors[0], a_positive)

    # Lagos: a routine request that was met and the donor confirmed as having given.
    routine = _raise(
        session, lagos, lagos_staff, group="O+", units=1, urgency=RequestUrgency.ROUTINE, hours=72
    )
    donated = _pledge(session, lagos_a_pos_donors[1], routine)
    resolve_pledge(session, lagos_staff, donated.id, donated=True, ip_address=None)

    # Lagos: a request whose deadline passed before anyone pledged.
    expired = BloodRequest(
        hospital_id=lagos.id,
        created_by=lagos_staff.id,
        recipient_group=BloodGroup.B_POSITIVE,
        component_type_id=routine.component_type_id,
        units_needed=2,
        urgency=RequestUrgency.URGENT,
        deadline=utcnow() - timedelta(hours=3),
        status=RequestStatus.OPEN,
    )
    session.add(expired)
    session.commit()
    expire_overdue(session, hospital_id=lagos.id)

    # Abuja: an urgent B+ request with one pledge.
    b_positive = _raise(
        session,
        abuja,
        abuja_staff,
        group="B+",
        units=2,
        urgency=RequestUrgency.URGENT,
        hours=12,
        notes="Sickle cell crisis, children's ward.",
    )
    _pledge(session, eligible_in("Abuja", "B+", "B-", "O+", "O-")[0], b_positive)

    # Enugu: a routine platelet request for a planned operation.
    _raise(
        session,
        enugu,
        enugu_staff,
        group="O+",
        units=2,
        urgency=RequestUrgency.ROUTINE,
        hours=48,
        component="platelets",
        notes="Scheduled surgery on Thursday morning.",
    )

    return _summary(session, created=True)
