"""Finding donors who can answer a blood request.

A donor is a match when all of these hold:

* their blood group is compatible with the patient's, according to the
  ``blood_compatibility`` table (the rules are data, not code);
* they are available, have agreed to be contacted, and their account is active;
* they are eligible to give the requested component today, using the same rules shown on
  their own dashboard (waiting period, age, weight, deferrals);
* they are within the search radius of the hospital.

Matches are ordered nearest first.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.models import (
    BloodCompatibility,
    BloodRequest,
    ComponentType,
    Donor,
    DonorDeferral,
    Hospital,
    User,
)
from app.services.distance import bounding_box, haversine_km
from app.services.eligibility import evaluate_eligibility


@dataclass(frozen=True)
class Match:
    """A donor who can answer a request, and how far away they are."""

    donor: Donor
    distance_km: float


def find_matches(
    session: Session,
    request: BloodRequest,
    hospital: Hospital,
    *,
    radius_km: float,
    limit: int,
    today: date | None = None,
) -> tuple[list[Match], int]:
    """Return the donors who match a request, nearest first.

    Args:
        session: An open database session.
        request: The request to answer.
        hospital: The hospital that raised it; its location is the search origin.
        radius_km: How far from the hospital to look.
        limit: The most matches to return.
        today: The day to judge eligibility on; defaults to the current UTC date.

    Returns:
        The nearest ``limit`` matches, and the total number of matches found.
    """
    component = session.get(ComponentType, request.component_type_id)
    if component is None:
        return [], 0

    compatible_groups = session.exec(
        select(BloodCompatibility.donor_group).where(
            BloodCompatibility.recipient_group == request.recipient_group
        )
    ).all()
    if not compatible_groups:
        return [], 0

    # Cheap filtering in the database: group, willingness and a rectangle around the
    # hospital. The exact distance and the eligibility rules are applied afterwards to the
    # much smaller set that remains.
    box = bounding_box(hospital.latitude, hospital.longitude, radius_km)
    candidates = session.exec(
        select(Donor)
        .join(User, col(User.id) == col(Donor.user_id))
        .where(
            col(Donor.blood_group).in_(compatible_groups),
            col(Donor.is_available).is_(True),
            col(Donor.consent_to_contact).is_(True),
            col(User.is_active).is_(True),
            col(Donor.latitude).between(box.min_lat, box.max_lat),
            col(Donor.longitude).between(box.min_lon, box.max_lon),
        )
    ).all()
    if not candidates:
        return [], 0

    # One query for every candidate's deferrals, instead of one query per donor.
    deferrals_by_donor: dict = defaultdict(list)
    for deferral in session.exec(
        select(DonorDeferral).where(col(DonorDeferral.donor_id).in_([d.id for d in candidates]))
    ).all():
        deferrals_by_donor[deferral.donor_id].append(deferral)

    settings = get_settings()
    on_day = today or datetime.now(UTC).date()

    matches: list[Match] = []
    for donor in candidates:
        distance = haversine_km(
            hospital.latitude, hospital.longitude, donor.latitude, donor.longitude
        )
        if distance > radius_km:
            continue

        result = evaluate_eligibility(
            donor,
            [component],
            deferrals_by_donor[donor.id],
            today=on_day,
            min_age_years=settings.min_donor_age_years,
            max_age_years=settings.max_donor_age_years,
            min_weight_kg=settings.min_donor_weight_kg,
        )
        if result.components[0].eligible:
            matches.append(Match(donor=donor, distance_km=distance))

    # Nearest first; the id breaks ties so the order is stable between calls.
    matches.sort(key=lambda match: (match.distance_km, str(match.donor.id)))
    return matches[:limit], len(matches)
