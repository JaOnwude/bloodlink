"""Tests of the postcode service. No test here reaches NIPOST: HTTP is answered by a mock."""

import httpx
import pytest
from sqlmodel import Session

from app.core.config import Settings
from app.services.postcode import (
    MockPostcodeClient,
    NipostClient,
    PostcodeServiceError,
    find_stored_lookup,
    get_postcode_client,
    lookup_postcode,
    normalise_postcode,
    parse_postcode,
    shared_ring,
)

BASE = "https://api.postcode.example"

# A level 3 answer in the shape NIPOST documents.
LEVEL_3_ANSWER = {
    "data": {
        "postcode": "EK-01-A03-FK-01",
        "valid": True,
        "administrative_address": {
            "state_name": "EKITI",
            "lga_name": "ADO EKITI",
            "locality_name": "ADO EKITI",
            "zone": "SOUTH WEST",
        },
        "recent_house_address": {"recent": "NTA ROAD, ADO EKITI"},
        "building_use_status": "residential",
    }
}


def nipost_with(
    handler, *, environment: str = "test", max_level: int = 3
) -> tuple[NipostClient, list[httpx.Request]]:
    """A NIPOST client whose HTTP calls go to ``handler`` instead of the network."""
    seen: list[httpx.Request] = []

    def record(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = NipostClient(
        api_key="nipost_test_secret",
        base_url=f"{BASE}/",
        environment=environment,
        max_level=max_level,
        timeout=5,
        client=httpx.Client(transport=httpx.MockTransport(record)),
    )
    return client, seen


# ---------------------------------------------------------------------------------------
# Reading postcodes as typed
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "typed", ["FC-01-A01-KP-27", "fc 01 a01 kp 27", "FC01A01KP27", " fc-01-a01-kp-27 "]
)
def test_case_spaces_and_dashes_do_not_matter(typed: str) -> None:
    assert normalise_postcode(typed) == "FC-01-A01-KP-27"


@pytest.mark.parametrize(
    "typed", ["", "FC-01-A01-KP", "FC-01-A01-KP-277", "12-01-A01-KP-27", "Abuja"]
)
def test_anything_not_shaped_like_a_postcode_is_rejected(typed: str) -> None:
    assert parse_postcode(typed) is None


def test_the_area_code_drops_only_the_building_unit() -> None:
    segments = parse_postcode("FC-01-A01-KP-27")

    assert segments is not None
    assert (segments.state, segments.lga, segments.district) == ("FC", "01", "A01")
    assert segments.area_code == "FC-01-A01-KP"


# ---------------------------------------------------------------------------------------
# The NIPOST client
# ---------------------------------------------------------------------------------------


def test_lookup_sends_the_key_header_and_reads_every_level_of_detail() -> None:
    client, seen = nipost_with(lambda _: httpx.Response(200, json=LEVEL_3_ANSWER))

    result = client.lookup("EK-01-A03-FK-01", 3)

    [request] = seen
    assert request.url.path == "/v1/lookup"
    assert request.url.params["code"] == "EK-01-A03-FK-01"
    assert request.url.params["level"] == "3"
    assert request.headers["X-API-Key"] == "nipost_test_secret"
    assert result.valid is True
    assert result.administrative_address is not None
    assert result.administrative_address.lga_name == "ADO EKITI"
    assert result.house_address == "NTA ROAD, ADO EKITI"
    assert result.building_use_status == "residential"


def test_lookup_is_capped_at_the_level_nipost_has_granted() -> None:
    client, seen = nipost_with(
        lambda _: httpx.Response(200, json={"data": {"postcode": "X", "valid": True}}),
        max_level=1,
    )

    result = client.lookup("EK-01-A03-FK-01", 3)

    assert seen[0].url.params["level"] == "1"
    assert result.level == 1
    assert result.administrative_address is None


def test_an_unassigned_postcode_is_reported_as_not_valid() -> None:
    client, _ = nipost_with(
        lambda _: httpx.Response(
            200, json={"data": {"postcode": "X", "valid": False, "status": "not_found"}}
        )
    )

    assert client.lookup("FC-01-A01-KP-27", 1).valid is False


def test_reverse_search_returns_the_nearest_building() -> None:
    answer = {
        "data": {
            "found": True,
            "unit": {"postcode": "FC01A01KP27", "distance_m": 12.5, "confidence": "high"},
        }
    }
    client, seen = nipost_with(lambda _: httpx.Response(200, json=answer))

    result = client.reverse(9.07, 7.39, 100)

    assert seen[0].url.path == "/v1/search/reverse"
    assert seen[0].url.params["max_distance_m"] == "100"
    assert result.found is True
    assert result.postcode == "FC-01-A01-KP-27"
    assert result.distance_m == 12.5


def test_reverse_search_with_nothing_in_range_finds_nothing() -> None:
    answer = {"data": {"found": False, "message": "no postcode within range"}}
    client, _ = nipost_with(lambda _: httpx.Response(200, json=answer))

    assert client.reverse(9.07, 7.39, 25).found is False


def test_lga_names_come_from_the_reference_data() -> None:
    answer = {"data": {"lgas": [{"code": "01", "name": "Abaji"}, {"code": "02", "name": "Bwari"}]}}
    client, seen = nipost_with(lambda _: httpx.Response(200, json=answer))

    assert client.lga_names("FC") == {"01": "Abaji", "02": "Bwari"}
    assert seen[0].url.params["state"] == "FC"


@pytest.mark.parametrize("status", [401, 402, 403, 429, 500])
def test_a_refusal_becomes_a_service_error_without_the_key(status: int) -> None:
    client, _ = nipost_with(
        lambda _: httpx.Response(status, json={"error": {"code": "x", "message": "no"}})
    )

    with pytest.raises(PostcodeServiceError) as caught:
        client.lookup("FC-01-A01-KP-27", 1)
    assert "nipost_test_secret" not in str(caught.value)


def test_an_unreachable_service_becomes_a_service_error() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    client, _ = nipost_with(fail)

    with pytest.raises(PostcodeServiceError):
        client.reverse(9.07, 7.39, 25)


# ---------------------------------------------------------------------------------------
# The mock and choosing a client
# ---------------------------------------------------------------------------------------


def test_the_mock_knows_the_nipost_sandbox_postcodes_only() -> None:
    mock = MockPostcodeClient()

    assert mock.lookup("FC-01-A01-KP-27", 1).valid is True
    assert mock.lookup("LA-01-A01-AA-01", 1).valid is False


def test_the_mock_adds_detail_level_by_level() -> None:
    mock = MockPostcodeClient()

    assert mock.lookup("FC-01-A01-KP-27", 1).administrative_address is None
    level_2 = mock.lookup("FC-01-A01-KP-27", 2)
    assert level_2.administrative_address is not None
    assert level_2.building_use_status is None
    assert mock.lookup("FC-01-A01-KP-27", 3).building_use_status == "public"


def test_the_mock_finds_a_sample_building_only_within_the_distance() -> None:
    mock = MockPostcodeClient()

    assert mock.reverse(9.0765, 7.3986, 25).postcode == "FC-01-A01-KP-27"
    assert mock.reverse(6.5244, 3.3792, 250).found is False


def test_mock_mode_never_needs_a_key() -> None:
    assert get_postcode_client(Settings(postcode_mode="mock")).name == "mock"


def test_a_matching_key_selects_nipost() -> None:
    settings = Settings(postcode_mode="test", nipost_api_key="nipost_test_abc")

    assert isinstance(get_postcode_client(settings), NipostClient)


@pytest.mark.parametrize("key", [None, "nipost_live_abc", "something-else"])
def test_a_missing_or_wrong_environment_key_falls_back_to_the_mock(
    key: str | None, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(postcode_mode="test", nipost_api_key=key)

    assert get_postcode_client(settings).name == "mock"
    assert "POSTCODE_MODE is test" in caplog.text


# ---------------------------------------------------------------------------------------
# Paying once per building
# ---------------------------------------------------------------------------------------


def test_a_paid_lookup_is_stored_and_reused(db_session: Session) -> None:
    client, seen = nipost_with(lambda _: httpx.Response(200, json=LEVEL_3_ANSWER))

    first = lookup_postcode(db_session, client, "EK-01-A03-FK-01", 2)
    again = lookup_postcode(db_session, client, "EK-01-A03-FK-01", 2)

    assert len(seen) == 1
    assert again.administrative_address == first.administrative_address
    stored = find_stored_lookup(db_session, "test", "EK-01-A03-FK-01")
    assert stored is not None
    assert stored.level == 2


def test_more_detail_than_stored_asks_nipost_again(db_session: Session) -> None:
    client, seen = nipost_with(lambda _: httpx.Response(200, json=LEVEL_3_ANSWER))

    lookup_postcode(db_session, client, "EK-01-A03-FK-01", 2)
    deeper = lookup_postcode(db_session, client, "EK-01-A03-FK-01", 3)

    assert len(seen) == 2
    assert deeper.building_use_status == "residential"
    assert find_stored_lookup(db_session, "test", "EK-01-A03-FK-01").level == 3


def test_free_level_1_lookups_are_never_stored(db_session: Session) -> None:
    client, seen = nipost_with(lambda _: httpx.Response(200, json=LEVEL_3_ANSWER))

    lookup_postcode(db_session, client, "EK-01-A03-FK-01", 1)
    lookup_postcode(db_session, client, "EK-01-A03-FK-01", 1)

    assert len(seen) == 2
    assert find_stored_lookup(db_session, "test", "EK-01-A03-FK-01") is None


def test_mock_answers_are_never_stored(db_session: Session) -> None:
    lookup_postcode(db_session, MockPostcodeClient(), "FC-01-A01-KP-27", 3)

    assert find_stored_lookup(db_session, "mock", "FC-01-A01-KP-27") is None


# ---------------------------------------------------------------------------------------
# Postcode rings between a hospital and a donor
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("donor_area", "ring"),
    [
        ("FC-01-A01-KP", "area"),
        ("FC-01-A01-LR", "district"),
        ("FC-01-B02-KP", "lga"),
        ("FC-02-A01-KP", "state"),
        ("LA-01-A01-KP", None),
        (None, None),
    ],
)
def test_the_closest_shared_ring_is_found(donor_area: str | None, ring: str | None) -> None:
    assert shared_ring("FC-01-A01-KP-27", donor_area) == ring


def test_a_hospital_without_a_postcode_shares_no_ring() -> None:
    assert shared_ring(None, "FC-01-A01-KP") is None


def test_the_mock_never_answers_above_the_granted_level() -> None:
    result = MockPostcodeClient(max_level=1).lookup("FC-01-A01-KP-27", 3)

    assert result.level == 1
    assert result.administrative_address is None
    assert result.building_use_status is None
