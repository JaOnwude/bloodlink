"""Dependencies shared by route handlers: database access, the signed-in user and role checks."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.config import get_settings
from app.core.security import TokenError, decode_access_token
from app.db.session import get_session
from app.models import Hospital, User
from app.models.enums import UserRole, VerificationStatus

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


# Reusable annotated types for routes restricted to one role. Declaring ``user: DonorUser``
# both signs the caller in (401 otherwise) and checks the role (403 otherwise).
DonorUser = Annotated[User, Depends(require_roles(UserRole.DONOR))]
StaffUser = Annotated[User, Depends(require_roles(UserRole.HOSPITAL_STAFF))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def get_client_ip(request: Request) -> str | None:
    """Return the network address of the caller, for the audit log.

    Behind a proxy or load balancer this is the proxy's address unless the platform is
    configured to forward the original one.
    """
    return request.client.host if request.client else None


ClientIp = Annotated[str | None, Depends(get_client_ip)]


def get_verified_hospital(staff: StaffUser, session: SessionDep) -> Hospital:
    """Return the staff member's hospital, provided an administrator has verified it.

    Features that act on behalf of a hospital, such as raising a blood request, depend on
    this. It keeps every alert that reaches a donor tied to a facility that has been vetted.

    Raises:
        HTTPException: 403 if the staff member has not registered a hospital, or if it is
            still pending or has been rejected.
    """
    if staff.hospital_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Register your hospital before using this feature.",
        )
    hospital = session.get(Hospital, staff.hospital_id)
    if hospital is None or hospital.verification_status != VerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your hospital has not been verified yet.",
        )
    return hospital


VerifiedHospital = Annotated[Hospital, Depends(get_verified_hospital)]
