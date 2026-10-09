"""Finding donors who can answer a blood request.

A donor is a match when all of these hold:

* their blood group is compatible with the patient's, according to the
  ``blood_compatibility`` table (the rules are data, not code);
* they are available, have agreed to be contacted, and their account is active;
* they do not already hold a pledge waiting to be resolved;
* they are eligible to give the requested component today, using the same rules shown on
  their own dashboard (waiting period, age, weight, deferrals);
* they are within the search radius of the hospital.

Matches are ordered nearest first.

The same rules also run in the other direction, from a donor to the open requests they can
answer, so what a donor is offered and what a hospital sees always agree.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.config import get_settings
from app.models import (
    BloodCompatibility,
    BloodRequest,
    ComponentType,
    Donor,
    DonorDeferral,
    Hospital,
    Pledge,
    User,
)
from app.models.enums import PledgeStatus, RequestStatus, RequestUrgency
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
            # A donor with a pledge waiting to be resolved cannot pledge again, whether it is
            # for this request or another, so offering them would only mislead.
            col(Donor.id).not_in(
                select(Pledge.donor_id).where(Pledge.status == PledgeStatus.PLEDGED)
            ),
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


@dataclass(frozen=True)
class RequestForDonor:
    """An open request a donor can answer, with where it is and how far away."""

    request: BloodRequest
    hospital: Hospital
    component: ComponentType
    distance_km: float
    units_remaining: int


# Most urgent first; within the same urgency, the soonest deadline first.
_URGENCY_ORDER = {RequestUrgency.CRITICAL: 0, RequestUrgency.URGENT: 1, RequestUrgency.ROUTINE: 2}


def find_requests_for_donor(
    session: Session,
    donor: Donor,
    *,
    radius_km: float,
    today: date | None = None,
) -> list[RequestForDonor]:
    """Return the open requests a donor can answer: matching seen from the donor's side.

    A request is included when the donor's group can be given to its patient (from the
    ``blood_compatibility`` table), its deadline is still ahead, it still needs units, its
    hospital is within ``radius_km`` of the donor, and the donor is eligible today for the
    component it asks for. Availability and contact consent are not required here: they
    govern whether the donor is alerted, while a donor who looks for requests themselves
    is free to answer one.

    Requests the donor has already pledged to are included as long as they are open, so the
    donor can see and cancel the pledge from the same list.

    Results are ordered by urgency, then deadline, then distance.
    """
    recipient_groups = session.exec(
        select(BloodCompatibility.recipient_group).where(
            BloodCompatibility.donor_group == donor.blood_group
        )
    ).all()
    if not recipient_groups:
        return []

    box = bounding_box(donor.latitude, donor.longitude, radius_km)
    rows = session.exec(
        select(BloodRequest, Hospital, ComponentType)
        .join(Hospital, col(Hospital.id) == col(BloodRequest.hospital_id))
        .join(ComponentType, col(ComponentType.id) == col(BloodRequest.component_type_id))
        .where(
            BloodRequest.status == RequestStatus.OPEN,
            col(BloodRequest.deadline) > datetime.now(UTC),
            col(BloodRequest.recipient_group).in_(recipient_groups),
            col(Hospital.latitude).between(box.min_lat, box.max_lat),
            col(Hospital.longitude).between(box.min_lon, box.max_lon),
        )
    ).all()
    if not rows:
        return []

    taken = dict(
        session.exec(
            select(Pledge.request_id, func.count())
            .where(
                col(Pledge.request_id).in_([request.id for request, _, _ in rows]),
                col(Pledge.status).in_((PledgeStatus.PLEDGED, PledgeStatus.DONATED)),
            )
            .group_by(Pledge.request_id)
        ).all()
    )

    deferrals = session.exec(select(DonorDeferral).where(DonorDeferral.donor_id == donor.id)).all()
    settings = get_settings()
    on_day = today or datetime.now(UTC).date()
    eligible_for: dict = {}

    results: list[RequestForDonor] = []
    for request, hospital, component in rows:
        distance = haversine_km(
            donor.latitude, donor.longitude, hospital.latitude, hospital.longitude
        )
        if distance > radius_km:
            continue
        remaining = request.units_needed - taken.get(request.id, 0)
        if remaining <= 0:
            continue
        if component.id not in eligible_for:
            result = evaluate_eligibility(
                donor,
                [component],
                deferrals,
                today=on_day,
                min_age_years=settings.min_donor_age_years,
                max_age_years=settings.max_donor_age_years,
                min_weight_kg=settings.min_donor_weight_kg,
            )
            eligible_for[component.id] = result.components[0].eligible
        if not eligible_for[component.id]:
            continue
        results.append(
            RequestForDonor(
                request=request,
                hospital=hospital,
                component=component,
                distance_km=distance,
                units_remaining=remaining,
            )
        )

    results.sort(
        key=lambda item: (
            _URGENCY_ORDER[item.request.urgency],
            item.request.deadline,
            item.distance_km,
            str(item.request.id),
        )
    )
    return results
