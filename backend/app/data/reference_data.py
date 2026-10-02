"""Reference data required for the application to function.

These constants are the single source of truth used to populate the ``blood_compatibility``
and ``component_types`` tables. At runtime the application reads the *tables*, never these
constants, so the rules can be corrected in the database without a code change. The
constants exist so that a fresh database can be initialised reproducibly and so that the
rules can be verified by automated tests.
"""

from app.models.enums import BloodGroup

_O_NEG = BloodGroup.O_NEGATIVE
_O_POS = BloodGroup.O_POSITIVE
_A_NEG = BloodGroup.A_NEGATIVE
_A_POS = BloodGroup.A_POSITIVE
_B_NEG = BloodGroup.B_NEGATIVE
_B_POS = BloodGroup.B_POSITIVE
_AB_NEG = BloodGroup.AB_NEGATIVE
_AB_POS = BloodGroup.AB_POSITIVE

# Standard red-cell compatibility chart: for each recipient group, the donor groups whose
# red cells that recipient can safely receive. Rh-negative recipients never receive
# Rh-positive red cells, and O-negative red cells are accepted by every recipient.
RED_CELL_COMPATIBILITY: dict[BloodGroup, tuple[BloodGroup, ...]] = {
    _O_NEG: (_O_NEG,),
    _O_POS: (_O_POS, _O_NEG),
    _A_NEG: (_A_NEG, _O_NEG),
    _A_POS: (_A_POS, _A_NEG, _O_POS, _O_NEG),
    _B_NEG: (_B_NEG, _O_NEG),
    _B_POS: (_B_POS, _B_NEG, _O_POS, _O_NEG),
    _AB_NEG: (_AB_NEG, _A_NEG, _B_NEG, _O_NEG),
    _AB_POS: (_AB_POS, _AB_NEG, _A_POS, _A_NEG, _B_POS, _B_NEG, _O_POS, _O_NEG),
}

# Donatable components and their minimum intervals between donations, in days.
#
# IMPORTANT: the interval values below are PLACEHOLDERS so the system can run end to end.
# They have not been verified against the national blood transfusion service or WHO
# guidance. They must be replaced with figures from those sources, cited in the project
# research notes, before the platform is used for anything beyond demonstration.
COMPONENT_TYPES: tuple[dict[str, str | int], ...] = (
    {
        "code": "whole_blood",
        "name": "Whole blood",
        "min_interval_days_male": 90,
        "min_interval_days_female": 120,
    },
    {
        "code": "platelets",
        "name": "Platelets",
        "min_interval_days_male": 14,
        "min_interval_days_female": 14,
    },
    {
        "code": "plasma",
        "name": "Plasma",
        "min_interval_days_male": 28,
        "min_interval_days_female": 28,
    },
)
