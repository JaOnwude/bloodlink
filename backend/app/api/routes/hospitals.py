"""Hospital registration endpoints for hospital staff.

Routes are scoped to the signed-in staff member's own hospital ("me"), so staff of one
facility can never see or change another facility's record.
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import ClientIp, SessionDep, StaffUser
from app.schemas.hospital import HospitalRead, HospitalWrite
from app.services.hospitals import (
    AlreadyHasHospitalError,
    HospitalNotFoundError,
    InvalidHospitalStateError,
    get_hospital_for_user,
    register_hospital,
    update_hospital,
)

router = APIRouter(prefix="/hospitals", tags=["hospitals"])

_NO_HOSPITAL = "You have not registered a hospital yet."


@router.post(
    "",
    response_model=HospitalRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register my hospital",
    responses={status.HTTP_409_CONFLICT: {"description": "Already registered a hospital"}},
)
def register_my_hospital(
    payload: HospitalWrite, user: StaffUser, session: SessionDep, ip_address: ClientIp
) -> HospitalRead:
    """Register a hospital and link the signed-in staff member to it.

    The hospital starts as ``pending``. It cannot raise blood requests until an
    administrator verifies it.
    """
    try:
        hospital = register_hospital(session, user, payload, ip_address=ip_address)
    except AlreadyHasHospitalError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your account is already linked to a hospital.",
        ) from None
    return HospitalRead.model_validate(hospital)


@router.get(
    "/me",
    response_model=HospitalRead,
    summary="Get my hospital and its verification status",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No hospital registered yet"}},
)
def read_my_hospital(user: StaffUser, session: SessionDep) -> HospitalRead:
    """Return the hospital the signed-in staff member belongs to."""
    hospital = get_hospital_for_user(session, user)
    if hospital is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NO_HOSPITAL)
    return HospitalRead.model_validate(hospital)


@router.put(
    "/me",
    response_model=HospitalRead,
    summary="Update my hospital's details",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No hospital registered yet"},
        status.HTTP_409_CONFLICT: {"description": "Hospital is already verified"},
    },
)
def update_my_hospital(
    payload: HospitalWrite, user: StaffUser, session: SessionDep, ip_address: ClientIp
) -> HospitalRead:
    """Correct the hospital's details while it is pending or after a rejection.

    Editing a rejected hospital sends it back to ``pending`` for another review.
    """
    try:
        hospital = update_hospital(session, user, payload, ip_address=ip_address)
    except HospitalNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NO_HOSPITAL) from None
    except InvalidHospitalStateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    return HospitalRead.model_validate(hospital)
