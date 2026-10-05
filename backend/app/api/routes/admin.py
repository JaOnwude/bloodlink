"""Administrator endpoints for reviewing hospital registrations.

Every route requires the administrator role. Each decision is written to the audit log with
the administrator's identity and network address.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AdminUser, ClientIp, SessionDep
from app.models import Hospital, User
from app.models.enums import VerificationStatus
from app.schemas.hospital import (
    AdminHospitalRead,
    HospitalPage,
    HospitalRead,
    RejectRequest,
    StaffSummary,
)
from app.services.hospitals import (
    HospitalNotFoundError,
    InvalidHospitalStateError,
    get_hospital,
    get_staff_by_hospital,
    list_hospitals,
    reject_hospital,
    verify_hospital,
)

router = APIRouter(prefix="/admin/hospitals", tags=["admin"])


def _to_admin_read(hospital: Hospital, staff: list[User]) -> AdminHospitalRead:
    """Combine a hospital with the staff accounts that registered it."""
    return AdminHospitalRead(
        **HospitalRead.model_validate(hospital).model_dump(),
        staff=[StaffSummary.model_validate(member) for member in staff],
    )


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hospital not found.")


@router.get("", response_model=HospitalPage, summary="Review queue of hospitals")
def list_registrations(
    admin: AdminUser,
    session: SessionDep,
    verification_status: Annotated[
        VerificationStatus,
        Query(alias="status", description="Only hospitals in this verification state."),
    ] = VerificationStatus.PENDING,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> HospitalPage:
    """List hospitals, oldest first. By default only those waiting for review."""
    hospitals, total = list_hospitals(
        session, status=verification_status, limit=limit, offset=offset
    )
    staff = get_staff_by_hospital(session, [hospital.id for hospital in hospitals])
    return HospitalPage(
        items=[_to_admin_read(hospital, staff[hospital.id]) for hospital in hospitals],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{hospital_id}",
    response_model=AdminHospitalRead,
    summary="Hospital details for review",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such hospital"}},
)
def read_registration(
    hospital_id: UUID, admin: AdminUser, session: SessionDep
) -> AdminHospitalRead:
    """Return one hospital together with the staff who registered it."""
    try:
        hospital = get_hospital(session, hospital_id)
    except HospitalNotFoundError:
        raise _not_found() from None
    staff = get_staff_by_hospital(session, [hospital.id])
    return _to_admin_read(hospital, staff[hospital.id])


@router.post(
    "/{hospital_id}/verify",
    response_model=AdminHospitalRead,
    summary="Verify a hospital",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such hospital"},
        status.HTTP_409_CONFLICT: {"description": "Already verified"},
    },
)
def verify_registration(
    hospital_id: UUID, admin: AdminUser, session: SessionDep, ip_address: ClientIp
) -> AdminHospitalRead:
    """Verify a hospital so its staff can raise blood requests."""
    try:
        hospital = verify_hospital(session, admin, hospital_id, ip_address=ip_address)
    except HospitalNotFoundError:
        raise _not_found() from None
    except InvalidHospitalStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    staff = get_staff_by_hospital(session, [hospital.id])
    return _to_admin_read(hospital, staff[hospital.id])


@router.post(
    "/{hospital_id}/reject",
    response_model=AdminHospitalRead,
    summary="Reject a hospital or revoke its verification",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such hospital"},
        status.HTTP_409_CONFLICT: {"description": "Already rejected"},
    },
)
def reject_registration(
    hospital_id: UUID,
    payload: RejectRequest,
    admin: AdminUser,
    session: SessionDep,
    ip_address: ClientIp,
) -> AdminHospitalRead:
    """Reject a pending hospital, or revoke a verified one, with a reason shown to its staff."""
    try:
        hospital = reject_hospital(
            session, admin, hospital_id, reason=payload.reason, ip_address=ip_address
        )
    except HospitalNotFoundError:
        raise _not_found() from None
    except InvalidHospitalStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    staff = get_staff_by_hospital(session, [hospital.id])
    return _to_admin_read(hospital, staff[hospital.id])
