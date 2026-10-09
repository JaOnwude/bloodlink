"""Donor profile, eligibility, the open requests a donor can answer, and their pledges.

Every route here is scoped to the signed-in donor ("me"): there is no identifier in the
URL, so one donor can never read or change another donor's profile.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlmodel import col, select

from app.api.deps import DonorUser, SessionDep
from app.core.config import get_settings
from app.models import Hospital, Pledge
from app.models.enums import PledgeStatus
from app.schemas.donor import (
    AvailabilityUpdate,
    ComponentEligibilityRead,
    DonorRead,
    DonorWrite,
    EligibilityRead,
)
from app.schemas.pledge import (
    DonorPledgePage,
    DonorPledgeRead,
    DonorRequestSummary,
    HospitalSummary,
    OpenRequestForDonor,
    OpenRequestsForDonor,
)
from app.schemas.request import MAX_SEARCH_RADIUS_KM
from app.services.donors import get_donor_for_user, save_donor_profile, set_availability
from app.services.eligibility import get_donor_eligibility
from app.services.matching import find_requests_for_donor
from app.services.pledges import list_donor_pledges

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


def _hospital_summary(hospital: Hospital) -> HospitalSummary:
    return HospitalSummary(
        id=hospital.id,
        name=hospital.name,
        address=hospital.address,
        city=hospital.city,
        state=hospital.state,
        contact_phone=hospital.contact_phone,
        latitude=hospital.latitude,
        longitude=hospital.longitude,
    )


@router.get(
    "/me/requests",
    response_model=OpenRequestsForDonor,
    summary="Open requests I can answer",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No profile yet"}},
)
def read_my_open_requests(
    user: DonorUser,
    session: SessionDep,
    radius_km: Annotated[float | None, Query(gt=0, le=MAX_SEARCH_RADIUS_KM)] = None,
) -> OpenRequestsForDonor:
    """List open requests near the donor that they are compatible with and eligible for.

    Ordered by urgency, then deadline, then distance. A request the donor has already
    pledged to stays in the list, marked with the pledge, while it is open.
    """
    donor = get_donor_for_user(session, user)
    if donor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NO_PROFILE)

    radius = radius_km if radius_km is not None else get_settings().default_search_radius_km
    found = find_requests_for_donor(session, donor, radius_km=radius)

    active = (
        dict(
            session.exec(
                select(Pledge.request_id, Pledge.id).where(
                    Pledge.donor_id == donor.id,
                    Pledge.status == PledgeStatus.PLEDGED,
                    col(Pledge.request_id).in_([item.request.id for item in found]),
                )
            ).all()
        )
        if found
        else {}
    )

    return OpenRequestsForDonor(
        items=[
            OpenRequestForDonor(
                id=item.request.id,
                recipient_group=item.request.recipient_group,
                component_code=item.component.code,
                component_name=item.component.name,
                urgency=item.request.urgency,
                deadline=item.request.deadline,
                notes=item.request.notes,
                units_remaining=item.units_remaining,
                distance_km=round(item.distance_km, 1),
                hospital=_hospital_summary(item.hospital),
                my_pledge_id=active.get(item.request.id),
            )
            for item in found
        ],
        radius_km=radius,
    )


@router.get(
    "/me/pledges",
    response_model=DonorPledgePage,
    summary="My pledges and donations",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No profile yet"}},
)
def read_my_pledges(
    user: DonorUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DonorPledgePage:
    """The donor's pledges, most recent first, with where to go and whom to call."""
    donor = get_donor_for_user(session, user)
    if donor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_NO_PROFILE)

    views, total = list_donor_pledges(session, donor, limit=limit, offset=offset)
    return DonorPledgePage(
        items=[
            DonorPledgeRead(
                id=view.pledge.id,
                status=view.pledge.status,
                pledged_at=view.pledge.pledged_at,
                resolved_at=view.pledge.resolved_at,
                request=DonorRequestSummary(
                    id=view.request.id,
                    recipient_group=view.request.recipient_group,
                    component_name=view.component.name,
                    urgency=view.request.urgency,
                    deadline=view.request.deadline,
                    notes=view.request.notes,
                    status=view.request.status,
                ),
                hospital=_hospital_summary(view.hospital),
            )
            for view in views
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
