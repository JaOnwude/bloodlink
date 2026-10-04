"""End-to-end tests of the authentication endpoints against a real PostgreSQL database.

They exercise the whole stack (request validation, password hashing, the database, the
cookie handling and the dependencies) the way a browser would, including the failure paths
an attacker would try.
"""

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.deps import require_roles
from app.core.config import get_settings
from app.models import User
from app.models.enums import UserRole
from app.services.auth import create_user

PASSWORD = "correct-horse-battery-staple-42"
BASE = "/api/v1/auth"


def payload(**overrides: object) -> dict[str, object]:
    """A valid registration body, with any field replaced by a keyword argument."""
    body: dict[str, object] = {
        "email": "ada@example.com",
        "password": PASSWORD,
        "full_name": "Ada Okafor",
        "role": "donor",
    }
    body.update(overrides)
    return body


def register(client: TestClient, **overrides: object):
    return client.post(f"{BASE}/register", json=payload(**overrides))


def login(client: TestClient, email: str = "ada@example.com", password: str = PASSWORD):
    return client.post(f"{BASE}/login", json={"email": email, "password": password})


# ---------------------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------------------


def test_registration_creates_the_account_and_signs_the_user_in(client: TestClient) -> None:
    response = register(client)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["role"] == "donor"
    assert "password" not in body
    assert "password_hash" not in body
    assert client.cookies.get(get_settings().auth_cookie_name)
    assert client.get(f"{BASE}/me").status_code == 200


def test_the_password_is_stored_as_a_hash(client: TestClient, db_session: Session) -> None:
    register(client)

    user = db_session.exec(select(User)).one()

    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash


def test_session_cookie_is_http_only_and_same_site_lax(client: TestClient) -> None:
    header = register(client).headers["set-cookie"].lower()

    assert "httponly" in header
    assert "samesite=lax" in header


def test_email_is_trimmed_and_lower_cased(client: TestClient) -> None:
    response = register(client, email="  Ada@Example.COM ")

    assert response.json()["email"] == "ada@example.com"


def test_the_same_email_cannot_register_twice_even_in_different_case(
    client: TestClient,
) -> None:
    assert register(client).status_code == 201

    second = register(client, email="ADA@example.com")

    assert second.status_code == 409


def test_administrators_cannot_be_self_registered(
    client: TestClient, db_session: Session
) -> None:
    response = register(client, role="admin")

    assert response.status_code == 422
    assert db_session.exec(select(User)).all() == []


def test_short_passwords_are_rejected_and_never_echoed_back(client: TestClient) -> None:
    response = register(client, password="Zx9-short")

    assert response.status_code == 422
    assert "Zx9-short" not in response.text


def test_common_passwords_are_rejected(client: TestClient) -> None:
    assert register(client, password="PasswordPassword").status_code == 422


def test_passwords_containing_the_email_name_are_rejected(client: TestClient) -> None:
    response = register(
        client, email="ada.okafor@example.com", password="ada.okafor-is-my-long-passphrase"
    )

    assert response.status_code == 422


def test_invalid_email_is_rejected(client: TestClient) -> None:
    assert register(client, email="not-an-email").status_code == 422


def test_invalid_phone_is_rejected(client: TestClient) -> None:
    assert register(client, phone="12ab").status_code == 422


def test_phone_separators_are_removed(client: TestClient, db_session: Session) -> None:
    register(client, phone="+234 803 123-4567")

    assert db_session.exec(select(User)).one().phone == "+2348031234567"


# ---------------------------------------------------------------------------------------
# Signing in and the current user
# ---------------------------------------------------------------------------------------


def test_login_then_me_returns_the_account(client: TestClient) -> None:
    register(client)
    client.cookies.clear()

    assert login(client).status_code == 200
    me = client.get(f"{BASE}/me")

    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"


def test_wrong_password_and_unknown_email_get_the_same_answer(client: TestClient) -> None:
    register(client)
    client.cookies.clear()

    wrong_password = login(client, password="not-the-right-password-at-all")
    unknown_email = login(client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_requires_a_session(client: TestClient) -> None:
    assert client.get(f"{BASE}/me").status_code == 401


def test_a_forged_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set(get_settings().auth_cookie_name, "not-a-real-token")

    assert client.get(f"{BASE}/me").status_code == 401


def test_logout_ends_the_session(client: TestClient) -> None:
    register(client)

    assert client.post(f"{BASE}/logout").status_code == 204
    assert client.get(f"{BASE}/me").status_code == 401


def test_logout_is_safe_when_nobody_is_signed_in(client: TestClient) -> None:
    assert client.post(f"{BASE}/logout").status_code == 204


def test_role_is_read_from_the_database_not_from_the_token(
    client: TestClient, db_session: Session
) -> None:
    register(client)
    user = db_session.exec(select(User)).one()
    user.role = UserRole.HOSPITAL_STAFF
    db_session.add(user)
    db_session.commit()

    assert client.get(f"{BASE}/me").json()["role"] == "hospital_staff"


def test_deactivated_accounts_lose_access_immediately(
    client: TestClient, db_session: Session
) -> None:
    register(client)
    user = db_session.exec(select(User)).one()
    user.is_active = False
    db_session.add(user)
    db_session.commit()

    assert client.get(f"{BASE}/me").status_code == 401
    client.cookies.clear()
    assert login(client).status_code == 401


# ---------------------------------------------------------------------------------------
# Throttling
# ---------------------------------------------------------------------------------------


def test_repeated_failures_lead_to_a_temporary_block(client: TestClient) -> None:
    register(client)
    client.cookies.clear()
    allowance = get_settings().login_max_failed_attempts

    for _ in range(allowance):
        assert login(client, password="wrong-password-wrong-password").status_code == 401

    blocked = login(client)  # even the correct password is refused while blocked

    assert blocked.status_code == 429
    assert "retry-after" in blocked.headers


def test_a_successful_sign_in_resets_the_failure_count(client: TestClient) -> None:
    register(client)
    client.cookies.clear()
    almost = get_settings().login_max_failed_attempts - 1

    for _ in range(almost):
        login(client, password="wrong-password-wrong-password")
    assert login(client).status_code == 200
    client.cookies.clear()
    for _ in range(almost):
        assert login(client, password="wrong-password-wrong-password").status_code == 401


# ---------------------------------------------------------------------------------------
# Services and role checks
# ---------------------------------------------------------------------------------------


def test_the_service_can_create_administrators(db_session: Session) -> None:
    admin = create_user(
        db_session,
        email="admin@example.com",
        password=PASSWORD,
        full_name="Site Admin",
        role=UserRole.ADMIN,
    )

    assert admin.role is UserRole.ADMIN


def test_role_guard_allows_listed_roles_and_refuses_others() -> None:
    guard = require_roles(UserRole.ADMIN)
    admin = User(email="a@example.com", password_hash="x", role=UserRole.ADMIN, full_name="A")
    donor = User(email="d@example.com", password_hash="x", role=UserRole.DONOR, full_name="D")

    assert guard(admin) is admin
    try:
        guard(donor)
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("A donor must not pass an admin-only guard.")
