"""Geographic distance calculations.

Donor matching ranks people by how far they are from the hospital. Two functions support
that: an exact great-circle distance, and a cheap bounding box used to discard far-away
donors in the database before any exact distance is computed.
"""

from dataclasses import dataclass
from math import asin, cos, degrees, radians, sin, sqrt

# Mean radius of the Earth in kilometres (IUGG).
EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres between two points given in degrees.

    The haversine formula is numerically stable for short distances, which is the common
    case here (donors within a few tens of kilometres of a hospital). The Earth is treated
    as a sphere, which is accurate to within about half a percent, far better than needed
    to rank nearby donors.
    """
    phi1, phi2 = radians(lat1), radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    # min() guards against a value a hair above 1 caused by floating-point rounding.
    return 2 * EARTH_RADIUS_KM * asin(min(1.0, sqrt(a)))


@dataclass(frozen=True)
class BoundingBox:
    """A rectangle of latitudes and longitudes."""

    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float


def bounding_box(lat: float, lon: float, radius_km: float) -> BoundingBox:
    """A rectangle that exactly contains the circle of ``radius_km`` around a point.

    On a sphere the circle reaches ``angular`` degrees north and south of its centre, and its
    widest point lies ``asin(sin(angular) / cos(latitude))`` degrees east and west of it.
    Using those exact extents guarantees no point inside the circle is ever left out. The
    rectangle is still larger than the circle (its corners are outside it), so it can only be
    used to discard points that are certainly too far; candidates inside it still need an
    exact distance check. It lets the database use ordinary indexes on latitude and longitude
    instead of computing a distance for every donor.

    A circle that reaches a pole spans every longitude, so the box then covers all of them.

    Known limitation: a circle that crosses the 180th meridian produces longitudes outside
    -180..180, which cannot occur for locations in Nigeria.
    """
    angular = radius_km / EARTH_RADIUS_KM
    lat_delta = degrees(angular)
    min_lat = max(-90.0, lat - lat_delta)
    max_lat = min(90.0, lat + lat_delta)

    cos_lat = cos(radians(lat))
    ratio = sin(angular) / cos_lat if cos_lat > 1e-12 else 2.0
    if ratio >= 1.0:
        return BoundingBox(min_lat=min_lat, max_lat=max_lat, min_lon=-180.0, max_lon=180.0)

    lon_delta = degrees(asin(ratio))
    return BoundingBox(
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=lon - lon_delta,
        max_lon=lon + lon_delta,
    )
