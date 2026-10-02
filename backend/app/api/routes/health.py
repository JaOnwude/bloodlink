"""Service health endpoints used by monitoring, load balancers and deployment platforms."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlmodel import Session

from app import __version__
from app.core.config import get_settings
from app.db.session import get_session
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
)
def liveness() -> HealthResponse:
    """Report that the API process is running.

    This endpoint deliberately does not touch the database. A liveness probe answers
    "should this process be restarted?", and a transient database outage is not a reason
    to restart a healthy API. Use the readiness probe to check dependencies.
    """
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=__version__,
        environment=settings.environment,
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database unreachable"}},
)
def readiness(session: Annotated[Session, Depends(get_session)]) -> ReadinessResponse:
    """Report whether the API can currently serve traffic that needs the database.

    Raises:
        HTTPException: With status 503 when the database cannot be queried, so that a
            load balancer stops routing requests to this instance until it recovers.
    """
    try:
        session.connection().execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - any failure means "not ready"
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return ReadinessResponse(status="ready", database="up")
