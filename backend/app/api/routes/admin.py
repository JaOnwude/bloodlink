"""Administrator endpoints for reviewing hospital registrations.

Every route requires the administrator role. Each decision is written to the audit log with
the administrator's identity and network address.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import AdminUser, ClientIp, SessionDep
from app.api.routes.postcodes import PostcodeClientDep
from app.models import Hospital, User
from app.models.enums import VerificationStatus
from app.schemas.hospital import (
    AdminHospitalRead,
    HospitalPage,
    HospitalRead,
    RejectRequest,
    StaffSummary,
)
from app.schemas.postcode import PostcodeRecordRead
from app.services.hospitals import (
    HospitalNotFoundError,
    InvalidHospitalStateError,
    get_hospital,
    get_staff_by_hospital,
    list_hospitals,
    reject_hospital,
    verify_hospital,
)
from app.services.postcode import PostcodeServiceError, lookup_postcode, parse_postcode

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


# The most detail an administrator's check asks for: level 3 adds what the building is used
# for. Capped by the level NIPOST has granted; paid answers are cached, so a hospital's
# building is paid for once however often it is reviewed.
_REVIEW_LEVEL = 3


@router.get(
    "/{hospital_id}/postcode-record",
    response_model=PostcodeRecordRead,
    summary="What NIPOST records about a hospital's building",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such hospital, or it has no postcode"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "NIPOST could not answer"},
    },
)
def read_postcode_record(
    hospital_id: UUID, _admin: AdminUser, session: SessionDep, postcodes: PostcodeClientDep
) -> PostcodeRecordRead:
    """Look the hospital's postcode up with NIPOST, to compare with what it registered.

    A "hospital" whose postcode belongs to a residential building, or to an address in
    another town, is worth a closer look before it is verified and can alert donors.
    """
    try:
        hospital = get_hospital(session, hospital_id)
    except HospitalNotFoundError:
        raise _not_found() from None
    segments = parse_postcode(hospital.postcode) if hospital.postcode else None
    if segments is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="This hospital gave no postcode."
        )

    try:
        result = lookup_postcode(session, postcodes, segments.postcode, _REVIEW_LEVEL)
        admin = result.administrative_address
        lga_name = admin.lga_name if admin else None
        if lga_name is None and result.valid:
            lga_name = postcodes.lga_names(segments.state).get(segments.lga)
    except PostcodeServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from None

    return PostcodeRecordRead(
        postcode=segments.postcode,
        valid=result.valid,
        level=result.level,
        state_name=admin.state_name if admin else None,
        lga_name=lga_name,
        locality_name=admin.locality_name if admin else None,
        house_address=result.house_address,
        building_use_status=result.building_use_status,
        source=postcodes.name,
    )
