"""Small helpers shared by the API tests."""

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import get_settings
from app.models import BloodRequest, ComponentType, Donor, Hospital, User
from app.models.base import utcnow
from app.models.enums import (
    BloodGroup,
    RequestStatus,
    RequestUrgency,
    Sex,
    UserRole,
    VerificationStatus,
)
from app.services.auth import create_user

PASSWORD = "correct-horse-battery-staple-42"
API = get_settings().api_prefix


def register_user(
    client: TestClient, *, email: str, role: str = "donor", full_name: str = "Test Person"
) -> dict:
    """Register an account through the API. The client is left signed in as that user."""
    response = client.post(
        f"{API}/auth/register",
        json={"email": email, "password": PASSWORD, "full_name": full_name, "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()


def sign_in(client: TestClient, email: str) -> None:
    """Discard the current session and sign in as ``email`` using the shared test password."""
    client.cookies.clear()
    response = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text


def make_admin(db_session: Session, email: str = "admin@example.com") -> User:
    """Create an administrator directly, as the command-line tool would."""
    return create_user(
        db_session,
        email=email,
        password=PASSWORD,
        full_name="Site Administrator",
        role=UserRole.ADMIN,
    )


def donor_payload(**overrides: object) -> dict[str, object]:
    """A valid donor profile body, with any field replaced by a keyword argument."""
    body: dict[str, object] = {
        "blood_group": "O-",
        "date_of_birth": "1995-06-15",
        "weight_kg": 72.5,
        "sex": "male",
        "latitude": 4.8156,
        "longitude": 7.0498,
        "city": "Port Harcourt",
        "is_available": True,
        "consent_to_contact": True,
    }
    body.update(overrides)
    return body


def hospital_payload(**overrides: object) -> dict[str, object]:
    """A valid hospital registration body, with any field replaced by a keyword argument."""
    body: dict[str, object] = {
        "name": "Rivers General Hospital",
        "address": "12 Hospital Road, Old GRA",
        "city": "Port Harcourt",
        "state": "Rivers",
        "latitude": 4.7719,
        "longitude": 7.0134,
        "registration_number": "RV-12345",
        "contact_phone": "+234 803 123 4567",
    }
    body.update(overrides)
    return body


def make_staff_with_hospital(
    db_session: Session,
    *,
    email: str = "staff1@example.com",
    status: VerificationStatus = VerificationStatus.VERIFIED,
    latitude: float = 6.5244,
    longitude: float = 3.3792,
    name: str = "Test Hospital",
) -> tuple[User, Hospital]:
    """Create a staff account (able to sign in) linked to a hospital in the given state."""
    staff = create_user(
        db_session,
        email=email,
        password=PASSWORD,
        full_name="Test Staff",
        role=UserRole.HOSPITAL_STAFF,
    )
    hospital = Hospital(
        name=name,
        address="1 Test Road, Lagos",
        city="Lagos",
        state="Lagos",
        latitude=latitude,
        longitude=longitude,
        contact_phone="+2348000000000",
        verification_status=status,
        verified_at=utcnow() if status == VerificationStatus.VERIFIED else None,
    )
    db_session.add(hospital)
    db_session.commit()
    staff.hospital_id = hospital.id
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)
    return staff, hospital


def make_donor_record(
    db_session: Session,
    *,
    email: str,
    blood_group: BloodGroup = BloodGroup.O_NEGATIVE,
    latitude: float = 6.5244,
    longitude: float = 3.3792,
    city: str = "Lagos",
    sex: Sex = Sex.MALE,
    weight_kg: float = 72.0,
    date_of_birth: date = date(1995, 6, 15),
    last_donation_date: date | None = None,
    is_available: bool = True,
    consent: bool = True,
    is_active: bool = True,
) -> Donor:
    """Insert a donor straight into the database, skipping password hashing for speed.

    The account cannot sign in; it exists so matching and counting can be tested.
    """
    user = User(
        email=email,
        password_hash="not-a-real-hash",
        role=UserRole.DONOR,
        full_name="Test Donor",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    donor = Donor(
        user_id=user.id,
        blood_group=blood_group,
        date_of_birth=date_of_birth,
        weight_kg=weight_kg,
        sex=sex,
        latitude=latitude,
        longitude=longitude,
        city=city,
        last_donation_date=last_donation_date,
        is_available=is_available,
        consent_to_contact=consent,
    )
    db_session.add(donor)
    db_session.commit()
    db_session.refresh(donor)
    return donor


def make_request_record(
    db_session: Session,
    hospital: Hospital,
    staff: User,
    *,
    recipient_group: BloodGroup = BloodGroup.O_NEGATIVE,
    component_code: str = "whole_blood",
    units_needed: int = 2,
    urgency: RequestUrgency = RequestUrgency.URGENT,
    deadline: datetime | None = None,
    status: RequestStatus = RequestStatus.OPEN,
) -> BloodRequest:
    """Insert a blood request straight into the database. Needs the reference data loaded."""
    component = db_session.exec(
        select(ComponentType).where(ComponentType.code == component_code)
    ).one()
    request = BloodRequest(
        hospital_id=hospital.id,
        created_by=staff.id,
        recipient_group=recipient_group,
        component_type_id=component.id,
        units_needed=units_needed,
        urgency=urgency,
        deadline=deadline or datetime.now(UTC) + timedelta(days=1),
        status=status,
    )
    db_session.add(request)
    db_session.commit()
    db_session.refresh(request)
    return request


def request_payload(**overrides: object) -> dict[str, object]:
    """A valid body for raising a request, with any field replaced by a keyword argument."""
    body: dict[str, object] = {
        "recipient_group": "O-",
        "component_code": "whole_blood",
        "units_needed": 2,
        "urgency": "urgent",
        "deadline": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "notes": "Ward 3, ask for the blood bank desk",
    }
    body.update(overrides)
    return body


# Central Lagos, where the default test hospital is.
LAGOS = {"latitude": 6.5244, "longitude": 3.3792, "city": "Lagos"}


def make_signed_in_donor(client: TestClient, *, email: str, **profile: object) -> str:
    """Register a donor through the API, create their profile in Lagos, and stay signed in.

    Profile fields can be replaced by keyword arguments. Returns the donor profile's id.
    """
    register_user(client, email=email, role="donor")
    response = client.put(f"{API}/donors/me", json=donor_payload(**{**LAGOS, **profile}))
    assert response.status_code == 201, response.text
    return response.json()["id"]
