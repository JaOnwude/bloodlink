"""FastAPI application entry point.

Run locally from the ``backend`` directory with:

    uv run uvicorn app.main:app --reload

Interactive documentation is then served at ``/api/v1/docs``.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Construction is wrapped in a factory so tests can create isolated instances and so
    configuration is read at a well-defined moment rather than at import time of unrelated
    modules.

    Returns:
        A fully configured ``FastAPI`` instance with CORS and all routes registered.
    """
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "BloodLink connects verified hospitals that urgently need blood with "
            "compatible, eligible and nearby donors, and tracks every pledge through to "
            "a confirmed donation."
        ),
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=None,
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    # The browser client authenticates with an httpOnly cookie, which requires an explicit
    # origin allow-list: wildcard origins are forbidden when credentials are allowed.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
