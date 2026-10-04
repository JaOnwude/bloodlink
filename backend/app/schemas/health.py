"""Response models for the service health endpoints."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Result of the liveness probe.

    Attributes:
        status: Always ``"ok"`` while the process is running and able to serve requests.
        service: Name of the service, useful when several APIs share a monitoring system.
        version: Deployed application version.
        environment: Deployment environment the process was started in.
    """

    status: Literal["ok"]
    service: str
    version: str
    environment: str


class ReadinessResponse(BaseModel):
    """Result of the readiness probe.

    Attributes:
        status: ``"ready"`` when every dependency required to serve traffic is available.
        database: ``"up"`` when a trivial query round-trips to PostgreSQL successfully.
    """

    status: Literal["ready"]
    database: Literal["up"]
