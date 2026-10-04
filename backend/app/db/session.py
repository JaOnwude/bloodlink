"""Database engine and session management.

A single SQLAlchemy engine (and its connection pool) is created for the whole process.
Request handlers obtain a short-lived ``Session`` through the ``get_session`` dependency,
which guarantees the session is closed when the request finishes, whether it succeeded
or raised an error.
"""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.core.config import get_settings

_settings = get_settings()

# ``pool_pre_ping`` validates a pooled connection before it is handed out. This
# transparently recovers from connections dropped by the database or by a managed
# hosting platform after periods of inactivity.
engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
)


def get_session() -> Generator[Session, None, None]:
    """Provide a database session scoped to a single request.

    Used as a FastAPI dependency:

        def handler(session: Session = Depends(get_session)): ...

    The caller is responsible for committing. Leaving the transaction uncommitted rolls
    it back when the session closes, which keeps read-only handlers side-effect free.

    Yields:
        An open ``Session`` bound to the shared engine.
    """
    with Session(engine) as session:
        yield session
