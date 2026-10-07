"""Small helpers shared by the API tests."""

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import get_settings
from app.models import User
from app.models.enums import UserRole
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
