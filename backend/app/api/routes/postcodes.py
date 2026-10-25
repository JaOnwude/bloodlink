"""Checking postcodes and finding them from a map position.

Both routes call NIPOST with BloodLink's own key, so they need a signed-in account: an
open endpoint would let anyone spend the key's rate limit. Neither route stores anything
about the caller, and a position sent to ``/postcodes/at`` is used for the one search and
then forgotten.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.schemas.postcode import PostcodeAtRead, PostcodeCheckRead
from app.services.postcode import (
    DEFAULT_REVERSE_DISTANCE_M,
    MAX_REVERSE_DISTANCE_M,
    PostcodeClient,
    PostcodeServiceError,
    get_postcode_client,
    lookup_postcode,
    parse_postcode,
)

router = APIRouter(prefix="/postcodes", tags=["postcodes"])

# The most detail a postcode check asks for: names of the state, LGA and locality. Capped
# by the level NIPOST has granted; the LGA name falls back to the free reference data.
_CHECK_LEVEL = 2


def postcode_client() -> PostcodeClient:
    """The postcode client chosen by the settings. Tests replace this dependency."""
    return get_postcode_client()


PostcodeClientDep = Annotated[PostcodeClient, Depends(postcode_client)]


def _unavailable(exc: PostcodeServiceError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


def require_assigned_postcode(client: PostcodeClient, postcode: str | None) -> None:
    """Refuse a postcode NIPOST has not assigned, with an error placed on the form field.

    Lookup level 1 is free, so this costs nothing. Nothing is checked when no postcode was
    given.

    Raises:
        HTTPException: 422 if the postcode is not assigned, 503 if NIPOST cannot answer.
    """
    if postcode is None:
        return
    try:
        result = client.lookup(postcode, 1)
    except PostcodeServiceError as exc:
        raise _unavailable(exc) from None
    if not result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                {
                    "loc": ["body", "postcode"],
                    "msg": f"NIPOST has no building with the postcode {postcode}. "
                    "Check it, or find it from the map.",
                    "type": "postcode_not_assigned",
                }
            ],
        )


@router.get(
    "/check",
    response_model=PostcodeCheckRead,
    summary="Check a postcode with NIPOST",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Not shaped like a postcode"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "NIPOST could not answer"},
    },
)
def check_postcode(
    code: Annotated[str, Query(min_length=1, max_length=40)],
    _user: CurrentUser,
    session: SessionDep,
    client: PostcodeClientDep,
) -> PostcodeCheckRead:
    """Say whether NIPOST has assigned a postcode, and which state and LGA it belongs to.

    The shape is checked first, without calling NIPOST. A well-shaped postcode is then
    looked up at level 2 when NIPOST has granted it (paid, and cached for every later
    check), otherwise at the free level 1. The LGA's name comes from NIPOST's free
    reference data when the lookup does not include it.
    """
    segments = parse_postcode(code)
    if segments is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Enter a full postcode of 11 letters and digits, like FC-01-A01-KP-27.",
        )

    try:
        result = lookup_postcode(session, client, segments.postcode, _CHECK_LEVEL)
    except PostcodeServiceError as exc:
        raise _unavailable(exc) from None

    admin = result.administrative_address
    lga_name = admin.lga_name if admin else None
    if lga_name is None and result.valid:
        try:
            lga_name = client.lga_names(segments.state).get(segments.lga)
        except PostcodeServiceError:
            # The name is a convenience; the check itself has already succeeded.
            lga_name = None

    return PostcodeCheckRead(
        postcode=segments.postcode,
        valid=result.valid,
        area_code=segments.area_code,
        state_code=segments.state,
        lga_code=segments.lga,
        state_name=admin.state_name if admin else None,
        lga_name=lga_name,
        locality_name=admin.locality_name if admin else None,
        source=client.name,
    )


@router.get(
    "/at",
    response_model=PostcodeAtRead,
    summary="Find the postcode of the building at a map position",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "NIPOST could not answer"}},
)
def postcode_at(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    _user: CurrentUser,
    client: PostcodeClientDep,
    max_distance_m: Annotated[
        int, Query(ge=1, le=MAX_REVERSE_DISTANCE_M)
    ] = DEFAULT_REVERSE_DISTANCE_M,
) -> PostcodeAtRead:
    """Return the postcode of the nearest building within ``max_distance_m`` metres.

    Uses NIPOST reverse search, which is free. The position is not stored.
    """
    try:
        result = client.reverse(latitude, longitude, max_distance_m)
    except PostcodeServiceError as exc:
        raise _unavailable(exc) from None
    return PostcodeAtRead(
        found=result.found,
        postcode=result.postcode,
        distance_m=result.distance_m,
        source=client.name,
    )
