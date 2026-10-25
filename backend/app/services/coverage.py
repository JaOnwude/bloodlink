"""How many donors a hospital can reach, ring by postcode ring.

A hospital with a postcode can see how many willing donors of each blood group live in its
own postcode area, its district, its LGA and its state. The rings are the same ones the
matching engine alerts in, so the figures say how far an appeal for O-negative will have to
reach before it finds anyone, and where a blood drive would add the most donors.

Only counts are reported. No donor is named, located or otherwise identified, and donors
who paused their alerts or did not agree to be contacted are not counted, because a hospital
could not reach them anyway.

Donors who have not given a postcode are counted separately, within the usual search
radius, so the hospital can see how much of its pool the postcode does not yet cover.
"""

from collections import Counter
from dataclasses import dataclass, field

from sqlmodel import Session, col, select

from app.models import Donor, Hospital, User
from app.models.enums import BloodGroup
from app.services.distance import bounding_box, haversine_km
from app.services.postcode import POSTCODE_RINGS, parse_postcode, shared_ring


@dataclass(frozen=True)
class RingCoverage:
    """Donors in one postcode ring around a hospital.

    Attributes:
        ring: ``area``, ``district``, ``lga`` or ``state``.
        prefix: The postcode segments the ring covers, for example ``FC-01`` for the LGA.
        total: Donors in the ring, counting the narrower rings inside it.
        by_group: The same donors by blood group.
    """

    ring: str
    prefix: str
    total: int
    by_group: dict[BloodGroup, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Coverage:
    """A hospital's reachable donors.

    Attributes:
        rings: One entry per ring, narrowest first. Empty when the hospital has no postcode.
        without_postcode_nearby: Reachable donors within ``radius_km`` with no postcode.
        radius_km: The radius used for ``without_postcode_nearby``.
    """

    rings: list[RingCoverage]
    without_postcode_nearby: int
    radius_km: float


def _reachable_donors():
    """Donors a hospital could alert: available, willing to be contacted, account active."""
    return (
        select(Donor)
        .join(User, col(User.id) == col(Donor.user_id))
        .where(
            col(Donor.is_available).is_(True),
            col(Donor.consent_to_contact).is_(True),
            col(User.is_active).is_(True),
        )
    )


def hospital_coverage(session: Session, hospital: Hospital, *, radius_km: float) -> Coverage:
    """Count the donors the hospital can reach, by postcode ring and blood group."""
    rings: list[RingCoverage] = []
    segments = parse_postcode(hospital.postcode) if hospital.postcode else None
    if segments is not None:
        in_state = session.exec(
            _reachable_donors().where(col(Donor.postcode_area).startswith(f"{segments.state}-"))
        ).all()
        counts = {ring: Counter() for ring in POSTCODE_RINGS}
        for donor in in_state:
            ring = shared_ring(segments.postcode, donor.postcode_area)
            if ring is None:
                continue
            # A donor in the hospital's own area is also in its district, LGA and state.
            for wider in POSTCODE_RINGS[POSTCODE_RINGS.index(ring) :]:
                counts[wider][donor.blood_group] += 1
        parts = segments.area_code.split("-")
        for index, ring in enumerate(POSTCODE_RINGS):
            prefix = "-".join(parts[: len(parts) - index])
            rings.append(
                RingCoverage(
                    ring=ring,
                    prefix=prefix,
                    total=sum(counts[ring].values()),
                    by_group=dict(counts[ring]),
                )
            )

    box = bounding_box(hospital.latitude, hospital.longitude, radius_km)
    nearby_without = session.exec(
        _reachable_donors().where(
            col(Donor.postcode_area).is_(None),
            col(Donor.latitude).between(box.min_lat, box.max_lat),
            col(Donor.longitude).between(box.min_lon, box.max_lon),
        )
    ).all()
    without_postcode = sum(
        1
        for donor in nearby_without
        if haversine_km(hospital.latitude, hospital.longitude, donor.latitude, donor.longitude)
        <= radius_km
    )
    return Coverage(rings=rings, without_postcode_nearby=without_postcode, radius_km=radius_km)
