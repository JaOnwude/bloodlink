"""Performance figures for hospital staff.

Only the signed-in staff member's own hospital is reported on; there is no identifier in
the URL, so one hospital can never read another's figures.
"""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep, StaffUser
from app.schemas.stats import HospitalStatsRead
from app.services.stats import hospital_stats

router = APIRouter(prefix="/stats", tags=["stats"])

# Longest period that can be asked for: one year.
MAX_PERIOD_DAYS = 365


@router.get(
    "/hospital",
    response_model=HospitalStatsRead,
    summary="My hospital's performance",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No hospital registered yet"}},
)
def read_hospital_stats(
    staff: StaffUser,
    session: SessionDep,
    days: Annotated[int, Query(ge=1, le=MAX_PERIOD_DAYS, description="Period in days")] = 30,
) -> HospitalStatsRead:
    """Fulfilment rate, median time to fulfil, no-show rate and totals for the period.

    Covers requests raised in the last ``days`` days. Rates are null when there is nothing
    to measure yet.
    """
    if staff.hospital_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Register your hospital to see its figures.",
        )
    stats = hospital_stats(session, staff.hospital_id, days=days)
    return HospitalStatsRead(**asdict(stats))
