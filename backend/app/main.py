"""FastAPI application entry point.

Run locally from the ``backend`` directory with:

    uv run uvicorn app.main:app --reload

Interactive documentation is then served at ``/api/v1/docs``.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.core.config import get_settings

# Prefix pydantic adds to messages that come from our own ValueError checks.
_VALUE_ERROR_PREFIX = "Value error, "


def _configure_logging() -> None:
    """Show the application's own log lines (alerts, SMS) next to the server's.

    Only the ``bloodlink`` loggers are configured, at INFO, and only once, so the server's
    and libraries' logging is left as it is. Log lines never contain tokens, passwords or
    full phone numbers.
    """
    app_logger = logging.getLogger("bloodlink")
    if app_logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s:     [%(name)s] %(message)s"))
    app_logger.addHandler(handler)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False


def create_app() -> FastAPI:
    """Build and configure the FastAPI application.

    Construction is wrapped in a factory so tests can create isolated instances and so
    configuration is read at a well-defined moment rather than at import time of unrelated
    modules.

    Returns:
        A fully configured ``FastAPI`` instance with CORS and all routes registered.
    """
    _configure_logging()
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

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Return validation problems in a compact, safe shape.

        FastAPI's default response echoes the rejected input back to the caller. For a
        registration request that includes the password, which could then end up in browser
        tools, proxies or log aggregators. This handler reports only where the problem is
        and what is wrong, and drops the internal context object that is not JSON-friendly.
        """
        errors = [
            {
                "loc": list(error["loc"]),
                "msg": error["msg"].removeprefix(_VALUE_ERROR_PREFIX),
                "type": error["type"],
            }
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": errors})

    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
