"""Performance figures for hospital staff.

Only the signed-in staff member's own hospital is reported on; there is no identifier in
the URL, so one hospital can never read another's figures.
"""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep, StaffUser
from app.api.routes.postcodes import PostcodeClientDep
from app.core.config import get_settings
from app.models import Hospital
from app.schemas.stats import CoverageRead, HospitalStatsRead, RingCoverageRead
from app.services.coverage import hospital_coverage
from app.services.postcode import PostcodeServiceError, parse_postcode
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


@router.get(
    "/coverage",
    response_model=CoverageRead,
    summary="Donors my hospital can reach, by postcode ring",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No hospital registered yet"}},
)
def read_coverage(
    staff: StaffUser, session: SessionDep, postcodes: PostcodeClientDep
) -> CoverageRead:
    """Count reachable donors in the hospital's postcode area, district, LGA and state.

    Counts only: no donor is identified. The LGA and state names come from NIPOST's free
    reference data; if NIPOST cannot answer, the figures are returned without them.
    """
    hospital = session.get(Hospital, staff.hospital_id) if staff.hospital_id else None
    if hospital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Register your hospital to see its figures.",
        )

    coverage = hospital_coverage(
        session, hospital, radius_km=get_settings().default_search_radius_km
    )
    names: dict[str, str | None] = {}
    segments = parse_postcode(hospital.postcode) if hospital.postcode else None
    if segments is not None:
        try:
            names["lga"] = postcodes.lga_names(segments.state).get(segments.lga)
        except PostcodeServiceError:
            names["lga"] = None
        names["state"] = hospital.state

    return CoverageRead(
        postcode=hospital.postcode,
        rings=[
            RingCoverageRead(
                ring=ring.ring,
                prefix=ring.prefix,
                name=names.get(ring.ring),
                total=ring.total,
                by_group={group.value: count for group, count in ring.by_group.items()},
            )
            for ring in coverage.rings
        ],
        without_postcode_nearby=coverage.without_postcode_nearby,
        radius_km=coverage.radius_km,
    )
