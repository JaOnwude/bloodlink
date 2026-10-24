"""Nigeria's digital postcode, through the NIPOST Postcode API or a built-in mock.

A postcode names one building in five segments: state, LGA, district, area and building
unit, for example ``FC-01-A01-KP-27``. BloodLink uses it three ways:

* **Checking.** Lookup level 1 (free) confirms a postcode is assigned before it is saved.
  Level 2 and up (paid) add the state, LGA and locality names, the recorded house address
  and, at level 3, what the building is used for.
* **Finding.** Reverse search (free) returns the postcode of the building at a map position,
  so nobody has to know their code by heart.
* **Grouping.** The segments themselves place a donor in an area, district, LGA and state
  without any further call.

Two clients share one small interface, so callers never know which is in use:

* ``NipostClient`` calls the NIPOST gateway with a secret key. A ``nipost_test_`` key reads
  NIPOST's sandbox; a ``nipost_live_`` key reads the production dataset. The endpoints and
  answers are identical, so switching is only a change of key.
* ``MockPostcodeClient`` answers from the sample buildings in ``app.data.postcode_samples``,
  which carry the postcodes NIPOST publishes for its sandbox. It needs no key or network,
  so automated tests and offline demonstrations use it. When a key is available, the free
  reference data (the names of LGAs) still comes from NIPOST.

``get_postcode_client`` picks the client from the settings. NIPOST is used only when it is
selected and the key belongs to the selected environment; otherwise the mock is used and
a warning says why.

Paid answers are cached in the ``postcode_lookups`` table by ``lookup_postcode``, so each
building is paid for once.

Privacy: the API key is never logged, and positions are not written to the log.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from sqlmodel import Session, select

from app.core.config import Settings, get_settings
from app.data.postcode_samples import (
    SAMPLE_BUILDINGS,
    SAMPLE_FCT_LGAS,
    SAMPLE_LGA_NAME,
    SAMPLE_STATE_NAME,
    SAMPLE_ZONE,
)
from app.models import PostcodeLookup
from app.models.base import utcnow
from app.services.distance import haversine_km

logger = logging.getLogger("bloodlink.postcode")

# Two letters (state), two digits (LGA), three letters or digits (district), two letters
# (area), two digits (building unit), once separators are removed.
_COMPACT_PATTERN = re.compile(r"([A-Z]{2})(\d{2})([A-Z0-9]{3})([A-Z]{2})(\d{2})")

# Characters people type between segments that carry no meaning.
_SEPARATORS = re.compile(r"[\s\-./]")

# NIPOST's own default and ceiling for reverse search, in metres.
DEFAULT_REVERSE_DISTANCE_M = 25
MAX_REVERSE_DISTANCE_M = 250

# Lookup levels that consume credits, and so are worth caching.
_FIRST_PAID_LEVEL = 2


class PostcodeServiceError(Exception):
    """Raised when NIPOST cannot answer. The message is safe to show to a user."""


@dataclass(frozen=True)
class PostcodeSegments:
    """The five parts of a postcode.

    Attributes:
        state: Two-letter state code, for example ``FC``.
        lga: Two-digit LGA code within the state.
        district: Three-character district code within the LGA.
        area: Two-letter area code within the district.
        unit: Two-digit building unit within the area.
    """

    state: str
    lga: str
    district: str
    area: str
    unit: str

    @property
    def postcode(self) -> str:
        """The full postcode in its dashed form, ``FC-01-A01-KP-27``."""
        return "-".join((self.state, self.lga, self.district, self.area, self.unit))

    @property
    def area_code(self) -> str:
        """The postcode without its building unit, ``FC-01-A01-KP``.

        This places someone in a neighbourhood without pointing at their building, which is
        all a donor's location needs to say.
        """
        return "-".join((self.state, self.lga, self.district, self.area))


def parse_postcode(raw: str) -> PostcodeSegments | None:
    """Split a postcode as typed into its segments, or return None if it is not one.

    Case, spaces and dashes are ignored, so ``fc 01 a01 kp 27``, ``FC01A01KP27`` and
    ``FC-01-A01-KP-27`` are the same postcode. This checks the shape only; whether NIPOST
    has assigned the code is a separate, online question answered by ``lookup``.
    """
    compact = _SEPARATORS.sub("", raw).upper()
    match = _COMPACT_PATTERN.fullmatch(compact)
    if match is None:
        return None
    return PostcodeSegments(*match.groups())


def normalise_postcode(raw: str) -> str | None:
    """Return the dashed form of a postcode as typed, or None if it is not one."""
    segments = parse_postcode(raw)
    return segments.postcode if segments else None


# How closely two postcodes agree, from the closest to the widest. A donor in the same area
# as a hospital is on its doorstep; one in the same state may be hours away.
POSTCODE_RINGS = ("area", "district", "lga", "state")


def shared_ring(hospital_postcode: str | None, donor_area: str | None) -> str | None:
    """The closest postcode ring a hospital and a donor share, or None if they share none.

    Compares the hospital's building postcode with the donor's area code segment by segment:
    the same state, LGA, district and area means ``"area"``; the same state, LGA and
    district means ``"district"``; and so on. Either side missing a postcode shares nothing.
    """
    if not hospital_postcode or not donor_area:
        return None
    hospital = hospital_postcode.split("-")[:4]
    donor = donor_area.split("-")[:4]
    shared = 0
    for ours, theirs in zip(hospital, donor, strict=False):
        if ours != theirs:
            break
        shared += 1
    if shared == 0:
        return None
    return POSTCODE_RINGS[len(POSTCODE_RINGS) - shared]


@dataclass(frozen=True)
class AdministrativeAddress:
    """The places a postcode belongs to, as NIPOST names them (level 2 and up)."""

    state_name: str | None
    lga_name: str | None
    locality_name: str | None
    zone: str | None


@dataclass(frozen=True)
class LookupResult:
    """NIPOST's answer about one postcode.

    Attributes:
        postcode: The postcode asked about, in its dashed form.
        valid: True when NIPOST has assigned the postcode to a building.
        level: The level of detail the answer was given at.
        administrative_address: State, LGA and locality names (level 2 and up).
        house_address: The most recent address recorded for the building (level 2 and up).
        building_use_status: What the building is used for (level 3 and up).
    """

    postcode: str
    valid: bool
    level: int
    administrative_address: AdministrativeAddress | None = None
    house_address: str | None = None
    building_use_status: str | None = None


@dataclass(frozen=True)
class ReverseResult:
    """The building nearest to a map position, if one is close enough.

    Attributes:
        found: True when a building lies within the distance searched.
        postcode: That building's postcode.
        distance_m: How far the building is from the position, in metres.
    """

    found: bool
    postcode: str | None = None
    distance_m: float | None = None


class PostcodeClient(Protocol):
    """Anything that can answer postcode questions."""

    name: str

    def lookup(self, postcode: str, level: int) -> LookupResult:
        """Describe ``postcode`` (dashed form) at ``level``. Raises PostcodeServiceError."""
        ...

    def reverse(self, latitude: float, longitude: float, max_distance_m: int) -> ReverseResult:
        """Find the building nearest to a position. Raises PostcodeServiceError."""
        ...

    def lga_names(self, state: str) -> dict[str, str]:
        """Map each LGA code in ``state`` to its name. Raises PostcodeServiceError."""
        ...


def _lookup_from_payload(data: dict[str, Any], postcode: str, level: int) -> LookupResult:
    """Read NIPOST's lookup answer (the inside of its ``data`` envelope)."""
    admin = data.get("administrative_address")
    house = data.get("recent_house_address")
    return LookupResult(
        postcode=postcode,
        valid=bool(data.get("valid")),
        level=level,
        administrative_address=(
            AdministrativeAddress(
                state_name=admin.get("state_name"),
                lga_name=admin.get("lga_name"),
                locality_name=admin.get("locality_name"),
                zone=admin.get("zone"),
            )
            if isinstance(admin, dict)
            else None
        ),
        house_address=house.get("recent") if isinstance(house, dict) else None,
        building_use_status=data.get("building_use_status"),
    )


class NipostClient:
    """Calls the NIPOST Postcode API.

    Args:
        api_key: A secret key (``nipost_test_`` or ``nipost_live_``).
        base_url: Address of the NIPOST gateway.
        environment: ``test`` or ``live``, matching the key. Used to label cached answers.
        max_level: Highest lookup level the organisation has been granted. Requests for
            more detail are capped here, because NIPOST refuses them outright.
        timeout: Seconds to wait for NIPOST before giving up.
        client: An HTTP client to use; tests pass one with a mock transport.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        environment: str,
        max_level: int,
        timeout: float,
        client: httpx.Client | None = None,
    ) -> None:
        self.name = environment
        self._base_url = base_url.rstrip("/")
        self._max_level = max_level
        self._client = client or httpx.Client(timeout=timeout)
        self._headers = {"X-API-Key": api_key, "Accept": "application/json"}

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """Call one endpoint and return the inside of its ``data`` envelope."""
        try:
            response = self._client.get(
                f"{self._base_url}{path}", params=params, headers=self._headers
            )
        except httpx.HTTPError as exc:
            logger.warning("NIPOST could not be reached: %s", type(exc).__name__)
            raise PostcodeServiceError(
                "The postcode service could not be reached. Try again in a moment."
            ) from None

        try:
            body = response.json()
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}

        if response.is_success and isinstance(body.get("data"), dict | list):
            data = body["data"]
            return data if isinstance(data, dict) else {"items": data}

        error = body.get("error") if isinstance(body.get("error"), dict) else {}
        logger.warning(
            "NIPOST refused %s (HTTP %s, %s)", path, response.status_code, error.get("code")
        )
        if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
            raise PostcodeServiceError("The postcode service is busy. Try again in a minute.")
        raise PostcodeServiceError("The postcode service could not check this right now.")

    def lookup(self, postcode: str, level: int) -> LookupResult:
        granted = max(1, min(level, self._max_level))
        data = self._get("/v1/lookup", {"code": postcode, "level": granted})
        return _lookup_from_payload(data, postcode, granted)

    def reverse(self, latitude: float, longitude: float, max_distance_m: int) -> ReverseResult:
        data = self._get(
            "/v1/search/reverse",
            {"lat": latitude, "lng": longitude, "max_distance_m": max_distance_m},
        )
        unit = data.get("unit") if isinstance(data.get("unit"), dict) else None
        if not data.get("found") or unit is None:
            return ReverseResult(found=False)
        postcode = normalise_postcode(str(unit.get("postcode") or unit.get("display") or ""))
        if postcode is None:
            return ReverseResult(found=False)
        distance = unit.get("distance_m")
        return ReverseResult(
            found=True,
            postcode=postcode,
            distance_m=float(distance) if isinstance(distance, int | float) else None,
        )

    def lga_names(self, state: str) -> dict[str, str]:
        data = self._get("/v1/reference/lgas", {"state": state})
        lgas = data.get("lgas")
        if not isinstance(lgas, list):
            return {}
        return {
            str(item["code"]): str(item["name"])
            for item in lgas
            if isinstance(item, dict) and "code" in item and "name" in item
        }


class MockPostcodeClient:
    """Answers from the sample buildings, without a key or network.

    Args:
        reference: A NIPOST client used for the free reference data, when a key is
            available. Without one, the names of the sample state's LGAs are built in.
        max_level: Highest lookup level to answer at, as NIPOST would cap it, so the mock
            never shows more detail than the organisation has been granted. Raise it in the
            settings to rehearse what a higher level will add.
    """

    name = "mock"

    def __init__(self, reference: NipostClient | None = None, max_level: int = 5) -> None:
        self._reference = reference
        self._max_level = max_level
        self._buildings = {building.postcode: building for building in SAMPLE_BUILDINGS}

    def lookup(self, postcode: str, level: int) -> LookupResult:
        level = max(1, min(level, self._max_level))
        building = self._buildings.get(postcode)
        if building is None:
            return LookupResult(postcode=postcode, valid=False, level=level)
        return LookupResult(
            postcode=postcode,
            valid=True,
            level=level,
            administrative_address=(
                AdministrativeAddress(
                    state_name=SAMPLE_STATE_NAME,
                    lga_name=SAMPLE_LGA_NAME,
                    locality_name=SAMPLE_LGA_NAME,
                    zone=SAMPLE_ZONE,
                )
                if level >= _FIRST_PAID_LEVEL
                else None
            ),
            house_address=building.house_address if level >= _FIRST_PAID_LEVEL else None,
            building_use_status=building.building_use_status if level >= 3 else None,
        )

    def reverse(self, latitude: float, longitude: float, max_distance_m: int) -> ReverseResult:
        nearest = min(
            SAMPLE_BUILDINGS,
            key=lambda b: haversine_km(latitude, longitude, b.latitude, b.longitude),
        )
        distance_m = haversine_km(latitude, longitude, nearest.latitude, nearest.longitude) * 1000
        if distance_m > max_distance_m:
            return ReverseResult(found=False)
        return ReverseResult(found=True, postcode=nearest.postcode, distance_m=round(distance_m, 1))

    def lga_names(self, state: str) -> dict[str, str]:
        if self._reference is not None:
            return self._reference.lga_names(state)
        return dict(SAMPLE_FCT_LGAS) if state == "FC" else {}


def _nipost_client(config: Settings, environment: str) -> NipostClient:
    assert config.nipost_api_key
    return NipostClient(
        api_key=config.nipost_api_key,
        base_url=config.nipost_base_url,
        environment=environment,
        max_level=config.nipost_max_lookup_level,
        timeout=config.postcode_timeout_seconds,
    )


def get_postcode_client(settings: Settings | None = None) -> PostcodeClient:
    """Return the client the settings ask for, falling back to the mock when needed."""
    config = settings or get_settings()
    if config.postcode_mode == "mock":
        reference = None
        if config.nipost_api_key:
            is_live = config.nipost_api_key.startswith("nipost_live_")
            reference = _nipost_client(config, "live" if is_live else "test")
        return MockPostcodeClient(reference=reference, max_level=config.nipost_max_lookup_level)

    if config.nipost_key_matches_mode:
        return _nipost_client(config, config.postcode_mode)

    logger.warning(
        "POSTCODE_MODE is %s but NIPOST_API_KEY is missing or is not a nipost_%s_ key, so "
        "postcodes are answered from the built-in samples.",
        config.postcode_mode,
        config.postcode_mode,
    )
    return MockPostcodeClient(max_level=config.nipost_max_lookup_level)


def find_stored_lookup(session: Session, source: str, postcode: str) -> PostcodeLookup | None:
    """Return the stored answer for a postcode from one source, if there is one."""
    return session.exec(
        select(PostcodeLookup).where(
            PostcodeLookup.source == source, PostcodeLookup.postcode == postcode
        )
    ).first()


def lookup_postcode(
    session: Session, client: PostcodeClient, postcode: str, level: int
) -> LookupResult:
    """Describe a postcode, reusing a stored answer for any paid level.

    Level 1 is free and always asked afresh. From level 2 up, a stored answer at the same
    or a higher level is reused; otherwise NIPOST is asked and its answer, if the postcode
    is valid, is stored. Answers from the mock are never stored.

    Raises:
        PostcodeServiceError: If NIPOST cannot answer and nothing is stored.
    """
    if level < _FIRST_PAID_LEVEL or client.name == "mock":
        return client.lookup(postcode, level)

    cached = find_stored_lookup(session, client.name, postcode)
    if cached is not None and cached.level >= level:
        return _lookup_from_payload(cached.payload, postcode, cached.level)

    result = client.lookup(postcode, level)
    if result.valid and result.level >= _FIRST_PAID_LEVEL:
        payload = _payload_from_lookup(result)
        if cached is None:
            session.add(
                PostcodeLookup(
                    source=client.name, postcode=postcode, level=result.level, payload=payload
                )
            )
        else:
            cached.level = result.level
            cached.payload = payload
            cached.fetched_at = utcnow()
            session.add(cached)
        session.commit()
    return result


def _payload_from_lookup(result: LookupResult) -> dict[str, Any]:
    """Store a lookup answer in the same shape NIPOST sends, so one reader handles both."""
    admin = result.administrative_address
    return {
        "postcode": result.postcode,
        "valid": result.valid,
        "administrative_address": (
            {
                "state_name": admin.state_name,
                "lga_name": admin.lga_name,
                "locality_name": admin.locality_name,
                "zone": admin.zone,
            }
            if admin
            else None
        ),
        "recent_house_address": (
            {"recent": result.house_address} if result.house_address is not None else None
        ),
        "building_use_status": result.building_use_status,
    }
