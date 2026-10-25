"""Sample buildings that the mock postcode service answers for.

The postcodes are the five that NIPOST publishes as its sandbox dataset: public buildings in
the Federal Capital Territory that "always resolve under a test key". Using the same codes
means the demonstration shows real NIPOST postcodes, and moving from the mock to the NIPOST
sandbox changes nothing that a user sees.

**What is invented.** NIPOST does not publish where these buildings stand or what their
addresses are, so the coordinates and address lines below are made up for the demonstration.
They are placed around the fictional Unity Teaching Hospital in the demonstration data
(central Abuja), so a hospital or donor pinned there finds one of them. The state and LGA
names come from NIPOST's own reference data for the ``FC`` and ``01`` segments.

Nothing here describes a real person's home. The sandbox, like this list, holds public
places only.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SampleBuilding:
    """One building the mock knows about.

    Attributes:
        postcode: The building's postcode in its dashed form.
        latitude: Invented position, used to answer reverse and nearby searches.
        longitude: Invented position.
        house_address: Invented address line, returned from Lookup level 2 upwards.
        building_use_status: What the building is used for, returned from level 3 upwards.
    """

    postcode: str
    latitude: float
    longitude: float
    house_address: str
    building_use_status: str


# Names NIPOST's reference data gives for the segments these postcodes share.
SAMPLE_STATE_NAME = "FEDERAL CAPITAL TERRITORY"
SAMPLE_LGA_NAME = "ABAJI"
SAMPLE_ZONE = "NORTH CENTRAL"

SAMPLE_BUILDINGS: tuple[SampleBuilding, ...] = (
    # At the demonstration's Unity Teaching Hospital.
    SampleBuilding("FC-01-A01-KP-27", 9.0765, 7.3986, "Sample public building 1", "public"),
    SampleBuilding("FC-01-A01-LR-01", 9.0841, 7.4102, "Sample public building 2", "public"),
    SampleBuilding("FC-01-A01-MH-01", 9.0652, 7.4213, "Sample public building 3", "public"),
    SampleBuilding("FC-01-A01-MV-01", 9.0583, 7.3847, "Sample public building 4", "public"),
    SampleBuilding("FC-01-A01-MW-01", 9.0927, 7.3791, "Sample public building 5", "public"),
)

# The LGAs NIPOST lists for the Federal Capital Territory, as returned by its reference API.
SAMPLE_FCT_LGAS: dict[str, str] = {
    "01": "Abaji",
    "02": "Abuja Municipal",
    "03": "Bwari",
    "04": "Gwagwalada",
    "05": "Kuje",
    "06": "Kwali",
}
