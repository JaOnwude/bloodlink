"""Authentication endpoints: register, sign in, sign out, and who-am-I.

The session is a signed token stored in an httpOnly cookie. Scripts running in the page
cannot read such a cookie, which removes the most common way tokens are stolen. The
``SameSite=Lax`` attribute stops browsers attaching it to cross-site form submissions,
which protects state-changing requests from cross-site request forgery.

Signing out clears the cookie in the browser. Because the token is stateless, a copy that
was already stolen would stay valid until it expires, which is why its lifetime is kept
modest and why the account is reloaded from the database on every request.
"""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.rate_limit import get_login_limiter
from app.core.security import create_access_token
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserRead
from app.services.auth import EmailAlreadyRegisteredError, authenticate, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, user: User) -> None:
    """Issue a session token for ``user`` and attach it to the response as a cookie."""
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_access_token(user.id, user.role),
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and sign in",
    responses={status.HTTP_409_CONFLICT: {"description": "Email already registered"}},
)
def register(payload: RegisterRequest, response: Response, session: SessionDep) -> UserRead:
    """Create a donor or hospital-staff account and sign the new user in.

    Administrator accounts cannot be created here. A staff member is linked to a hospital
    after registering.
    """
    try:
        user = create_user(
            session,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role,
            phone=payload.phone,
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        ) from None

    _set_session_cookie(response, user)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=UserRead,
    summary="Sign in",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid email or password"},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too many failed attempts"},
    },
)
def login(
    payload: LoginRequest, request: Request, response: Response, session: SessionDep
) -> UserRead:
    """Verify credentials and start a session.

    Repeated failures for the same address and email are throttled. Every failure returns
    the same message, so the response never reveals whether an email is registered.
    """
    settings = get_settings()
    limiter = get_login_limiter()
    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}|{payload.email}"

    if limiter.is_blocked(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed sign-in attempts. Please wait and try again.",
            headers={"Retry-After": str(settings.login_window_seconds)},
        )

    user = authenticate(session, payload.email, payload.password)
    if user is None:
        limiter.record_failure(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    limiter.reset(key)
    _set_session_cookie(response, user)
    return UserRead.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out",
)
def logout() -> Response:
    """End the session by clearing the cookie. Safe to call when nobody is signed in."""
    settings = get_settings()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )
    return response


@router.get(
    "/me",
    response_model=UserRead,
    summary="Current user",
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Not signed in"}},
)
def me(user: CurrentUser) -> UserRead:
    """Return the account that owns the current session."""
    return UserRead.model_validate(user)
