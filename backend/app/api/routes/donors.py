"""Donor profile and eligibility endpoints.

Every route here is scoped to the signed-in donor ("me"): there is no identifier in the
URL, so one donor can never read or change another donor's profile.
"""

from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import DonorUser, SessionDep
from app.schemas.donor import (
    AvailabilityUpdate,
    ComponentEligibilityRead,
    DonorRead,
    DonorWrite,
    EligibilityRead,
)
from app.services.donors import get_donor_for_user, save_donor_profile, set_availability
from app.services.eligibility import get_donor_eligibility

router = APIRouter(prefix="/donors", tags=["donors"])

_NO_PROFILE = "You have not created a donor profile yet."


@router.get(
    "/me",
    response_model=DonorRead,
    summary="Get my donor profile",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No profile yet"}},
)
def read_my_profile(user: DonorUser, session: SessionDep) -> DonorRead:
    """Return the signed-in donor's profile."""
    donor = get_donor_for_user(session, user)
    if donor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NO_PROFILE)
    return DonorRead.model_validate(donor)


@router.put(
    "/me",
    response_model=DonorRead,
    summary="Create or replace my donor profile",
)
def save_my_profile(
    payload: DonorWrite, user: DonorUser, response: Response, session: SessionDep
) -> DonorRead:
    """Create the profile on first use, or replace it afterwards.

    Returns 201 when the profile was created and 200 when an existing one was updated.
    """
    donor, created = save_donor_profile(session, user, payload)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return DonorRead.model_validate(donor)


@router.patch(
    "/me/availability",
    response_model=DonorRead,
    summary="Turn alerts on or off",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No profile yet"}},
)
def update_my_availability(
    payload: AvailabilityUpdate, user: DonorUser, session: SessionDep
) -> DonorRead:
    """Pause or resume alerts without changing the rest of the profile."""
    donor = get_donor_for_user(session, user)
    if donor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NO_PROFILE)
    donor = set_availability(session, donor, is_available=payload.is_available)
    return DonorRead.model_validate(donor)


@router.get(
    "/me/eligibility",
    response_model=EligibilityRead,
    summary="Check what I can donate today",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No profile yet"}},
)
def read_my_eligibility(user: DonorUser, session: SessionDep) -> EligibilityRead:
    """Report, per kind of donation, whether the donor may give today and if not, from when.

    This is guidance based on the details the donor entered. Final eligibility is decided
    by clinical staff at the donation site.
    """
    donor = get_donor_for_user(session, user)
    if donor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NO_PROFILE)
    result = get_donor_eligibility(session, donor)
    return EligibilityRead(
        eligible_for_any=result.eligible_for_any,
        blockers=list(result.blockers),
        components=[
            ComponentEligibilityRead(
                component_code=item.code,
                component_name=item.name,
                eligible=item.eligible,
                next_eligible_date=item.next_eligible_date,
            )
            for item in result.components
        ],
    )
