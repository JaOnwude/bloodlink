"""Shared test fixtures.

Tests that talk to the database run against a separate PostgreSQL database named after the
real one with a ``_test`` suffix (for example ``bloodlink_test``), created on demand inside
the same Docker container. The development database is never touched.

PostgreSQL must be running for those tests (``docker compose up -d db``). If it is not
reachable, the tests that need it are skipped with an explanatory message instead of
failing, so the database-free tests can still be run on their own.

The schema is built from the model definitions at the start of each run. Migrations are
verified separately by running them against the development database.
"""

import re
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine

import app.models  # noqa: F401  (registers every table on SQLModel.metadata)
from app.core.config import get_settings
from app.core.rate_limit import get_login_limiter
from app.db.seed import seed_reference_data
from app.db.session import get_session
from app.main import app


def _truncate_all_tables(engine: Engine) -> None:
    """Empty every table so each test starts from a clean database."""
    tables = ", ".join(f'"{table.name}"' for table in SQLModel.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Engine for the dedicated test database, created and prepared once per run."""
    base_url = make_url(get_settings().database_url)
    test_name = f"{base_url.database}_test"
    # The name is interpolated into a CREATE DATABASE statement, which cannot be
    # parameterised, so it must be restricted to safe characters.
    assert re.fullmatch(r"[A-Za-z0-9_]+", test_name), f"Unsafe database name: {test_name}"

    try:
        admin_engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": test_name}
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{test_name}"'))
        admin_engine.dispose()
    except OperationalError as exc:
        pytest.skip(
            "PostgreSQL is not reachable, so database tests were skipped "
            f"({exc.__class__.__name__}). Start it with: docker compose up -d db"
        )

    engine = create_engine(base_url.set(database=test_name), pool_pre_ping=True)
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_database(db_engine: Engine) -> Generator[None, None, None]:
    """Empty all tables after the test, whatever its outcome."""
    try:
        yield
    finally:
        _truncate_all_tables(db_engine)


@pytest.fixture
def db_session(db_engine: Engine, clean_database: None) -> Generator[Session, None, None]:
    """A session on the test database, for arranging and inspecting data directly."""
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def client(db_engine: Engine, clean_database: None) -> Generator[TestClient, None, None]:
    """A test client whose requests use the test database.

    The client keeps cookies between requests, like a browser, so a sign-in carries over
    to later calls in the same test. The login throttle is reset so tests cannot affect
    each other.
    """

    def override_get_session() -> Generator[Session, None, None]:
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    get_login_limiter().clear()
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        get_login_limiter().clear()


@pytest.fixture
def reference_data(db_session: Session) -> None:
    """Load the blood compatibility chart and component types into the test database."""
    seed_reference_data(db_session)


@pytest.fixture(autouse=True)
def never_send_real_sms(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the console sender in every test, whatever ``.env`` says.

    Termii has no sandbox, so a test that reached it would send a real, paid message. Tests
    that check the Termii sender build it themselves with a mock transport.
    """
    monkeypatch.setattr(get_settings(), "sms_provider", "console")
