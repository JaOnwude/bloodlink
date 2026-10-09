"""Tests of the distance calculations. No database is needed."""

from math import asin, atan2, cos, degrees, radians, sin

import pytest

from app.services.distance import (
    EARTH_RADIUS_KM,
    approximate_position,
    bounding_box,
    haversine_km,
)

LAGOS = (6.5244, 3.3792)
ABUJA = (9.0765, 7.3986)


def destination_point(
    lat: float, lon: float, bearing_degrees: float, distance_km: float
) -> tuple[float, float]:
    """The point reached by travelling a distance from a start along a bearing.

    An independent calculation (the standard great-circle destination formula), used to
    build points that lie exactly on a circle around the start.
    """
    delta = distance_km / EARTH_RADIUS_KM
    phi1, lam1, theta = radians(lat), radians(lon), radians(bearing_degrees)
    phi2 = asin(sin(phi1) * cos(delta) + cos(phi1) * sin(delta) * cos(theta))
    lam2 = lam1 + atan2(sin(theta) * sin(delta) * cos(phi1), cos(delta) - sin(phi1) * sin(phi2))
    return degrees(phi2), degrees(lam2)


def test_the_same_point_is_zero_kilometres_away() -> None:
    assert haversine_km(*LAGOS, *LAGOS) == 0.0


def test_one_degree_of_latitude_is_about_111_kilometres() -> None:
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.19, abs=0.1)


def test_a_quarter_of_the_equator_is_a_quarter_of_the_circumference() -> None:
    quarter = 3.141592653589793 * EARTH_RADIUS_KM / 2
    assert haversine_km(0, 0, 0, 90) == pytest.approx(quarter, rel=1e-6)


def test_distance_is_the_same_in_both_directions() -> None:
    assert haversine_km(*LAGOS, *ABUJA) == pytest.approx(haversine_km(*ABUJA, *LAGOS))


def test_lagos_to_abuja_is_roughly_five_hundred_and_thirty_kilometres() -> None:
    assert 515 < haversine_km(*LAGOS, *ABUJA) < 540


def test_short_distances_are_accurate() -> None:
    """A tenth of a degree of latitude is about 11.1 km."""
    assert haversine_km(6.5244, 3.3792, 6.6244, 3.3792) == pytest.approx(11.12, abs=0.05)


def test_destination_points_really_are_the_requested_distance_away() -> None:
    """Checks the helper above against the function under test."""
    for bearing in range(0, 360, 30):
        lat, lon = destination_point(*LAGOS, bearing, 25.0)
        assert haversine_km(*LAGOS, lat, lon) == pytest.approx(25.0, abs=1e-6)


def test_the_bounding_box_contains_every_point_on_the_circle() -> None:
    """Points exactly on the radius, in every direction, are inside the box."""
    box = bounding_box(*LAGOS, 25.0)
    tolerance = 1e-9

    for bearing in range(0, 360, 5):
        lat, lon = destination_point(*LAGOS, bearing, 25.0)
        assert box.min_lat - tolerance <= lat <= box.max_lat + tolerance, bearing
        assert box.min_lon - tolerance <= lon <= box.max_lon + tolerance, bearing


def test_the_bounding_box_contains_circles_at_other_latitudes() -> None:
    for lat, lon in (ABUJA, (12.0022, 8.592), (4.8156, 7.0498)):
        box = bounding_box(lat, lon, 60.0)
        for bearing in range(0, 360, 10):
            point_lat, point_lon = destination_point(lat, lon, bearing, 60.0)
            assert box.min_lat - 1e-9 <= point_lat <= box.max_lat + 1e-9
            assert box.min_lon - 1e-9 <= point_lon <= box.max_lon + 1e-9


def test_the_bounding_box_excludes_far_points() -> None:
    box = bounding_box(*LAGOS, 25.0)

    assert not (box.min_lat <= 7.5 <= box.max_lat)  # about 108 km north
    assert not (box.min_lon <= 5.0 <= box.max_lon)  # about 180 km east


def test_the_bounding_box_is_centred_on_the_point() -> None:
    box = bounding_box(*LAGOS, 25.0)

    assert (box.min_lat + box.max_lat) / 2 == pytest.approx(LAGOS[0])
    assert (box.min_lon + box.max_lon) / 2 == pytest.approx(LAGOS[1])


def test_a_circle_that_reaches_a_pole_covers_every_longitude() -> None:
    box = bounding_box(89.9, 0.0, 50.0)

    assert box.min_lon == -180.0
    assert box.max_lon == 180.0
    assert box.max_lat == 90.0


def test_approximate_positions_hide_the_exact_point() -> None:
    # Two homes a few hundred metres apart land on the same grid point.
    first = approximate_position(6.534567, 3.384321)
    second = approximate_position(6.531200, 3.381900)

    assert first == second == (6.53, 3.38)
