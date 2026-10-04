"""Dependencies shared by route handlers: database access, the signed-in user and role checks."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.config import get_settings
from app.core.security import TokenError, decode_access_token
from app.db.session import get_session
from app.models import User
from app.models.enums import UserRole

# Reusable annotated type so handlers can simply declare ``session: SessionDep``.
SessionDep = Annotated[Session, Depends(get_session)]


def _not_authenticated() -> HTTPException:
    """Build the single answer given for every kind of authentication failure.

    A missing cookie, a forged token, an expired token and a deleted or deactivated
    account all look identical to the caller, so the response reveals nothing useful to an
    attacker probing the endpoint.
    """
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")


def get_current_user(request: Request, session: SessionDep) -> User:
    """Resolve the account that owns the session cookie on this request.

    The token proves who the caller is, but the account is always reloaded from the
    database. That makes changes take effect immediately: a deactivated account stops
    working on its next request, and a changed role applies at once, even though the old
    token has not yet expired.

    Raises:
        HTTPException: 401 when there is no valid session for an active account.
    """
    token = request.cookies.get(get_settings().auth_cookie_name)
    if not token:
        raise _not_authenticated()

    try:
        claims = decode_access_token(token)
    except TokenError:
        raise _not_authenticated() from None

    user = session.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise _not_authenticated()
    return user


# Reusable annotated type so handlers can simply declare ``user: CurrentUser``.
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: UserRole) -> Callable[[User], User]:
    """Create a dependency that only lets accounts with one of the given roles through.

    Usage:

        @router.get("/admin/hospitals")
        def pending(admin: Annotated[User, Depends(require_roles(UserRole.ADMIN))]): ...

    The role checked is the one stored in the database, taken from the freshly loaded
    account, never the role written into the token.

    Raises (when the returned dependency runs):
        HTTPException: 401 if nobody is signed in, 403 if the role is not permitted.
    """

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return user

    return dependency
