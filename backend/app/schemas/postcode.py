"""Response models for postcode checks and searches."""

from pydantic import BaseModel


class PostcodeCheckRead(BaseModel):
    """What BloodLink knows about one postcode.

    Attributes:
        postcode: The postcode in its dashed form, ``FC-01-A01-KP-27``.
        valid: True when NIPOST has assigned it to a building.
        area_code: The postcode without its building unit: all a donor's profile keeps.
        state_code: The state segment, for example ``FC``.
        lga_code: The LGA segment within the state, for example ``01``.
        state_name: The state's name, when NIPOST gave it (lookup level 2 and up).
        lga_name: The LGA's name, from NIPOST's free reference data when the lookup level
            does not include it.
        locality_name: The town or locality, when NIPOST gave it (level 2 and up).
        source: Which dataset answered: ``mock`` (built-in samples), ``test`` (the NIPOST
            sandbox) or ``live``.
    """

    postcode: str
    valid: bool
    area_code: str
    state_code: str
    lga_code: str
    state_name: str | None
    lga_name: str | None
    locality_name: str | None
    source: str


class PostcodeAtRead(BaseModel):
    """The building nearest to a map position.

    Attributes:
        found: True when a building with a postcode lies close enough.
        postcode: That building's postcode.
        distance_m: How far it is from the position, in metres.
        source: Which dataset answered (see ``PostcodeCheckRead.source``).
    """

    found: bool
    postcode: str | None
    distance_m: float | None
    source: str


class PostcodeRecordRead(BaseModel):
    """What NIPOST records about a hospital's building, for an administrator reviewing it.

    Attributes:
        postcode: The hospital's postcode.
        valid: True when NIPOST has assigned it to a building.
        level: The lookup level NIPOST answered at. Fields beyond it are empty.
        state_name: State, from level 2.
        lga_name: LGA, from level 2, or NIPOST's free reference data below that.
        locality_name: Town or locality, from level 2.
        house_address: The most recent address NIPOST holds for the building, from level 2.
        building_use_status: What the building is used for, from level 3.
        source: Which dataset answered (see ``PostcodeCheckRead.source``).
    """

    postcode: str
    valid: bool
    level: int
    state_name: str | None
    lga_name: str | None
    locality_name: str | None
    house_address: str | None
    building_use_status: str | None
    source: str
