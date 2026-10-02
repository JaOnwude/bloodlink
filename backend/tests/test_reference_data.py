"""Tests that verify the blood compatibility chart and component seed data.

These tests guard the correctness of the rules the matching engine will depend on. They
run without a database because they exercise the constants used to populate it.
"""

from app.data.reference_data import COMPONENT_TYPES, RED_CELL_COMPATIBILITY
from app.models.enums import BloodGroup


def _is_rh_negative(group: BloodGroup) -> bool:
    return group.value.endswith("-")


def test_every_blood_group_has_an_entry() -> None:
    """All eight groups appear as recipients."""
    assert set(RED_CELL_COMPATIBILITY) == set(BloodGroup)


def test_every_group_can_receive_its_own_group() -> None:
    """A recipient is always compatible with donors of the identical group."""
    for recipient, donors in RED_CELL_COMPATIBILITY.items():
        assert recipient in donors


def test_o_negative_is_the_universal_red_cell_donor() -> None:
    """O-negative red cells are acceptable to every recipient."""
    for donors in RED_CELL_COMPATIBILITY.values():
        assert BloodGroup.O_NEGATIVE in donors


def test_ab_positive_receives_from_every_group() -> None:
    """AB-positive is the universal red-cell recipient."""
    assert set(RED_CELL_COMPATIBILITY[BloodGroup.AB_POSITIVE]) == set(BloodGroup)


def test_rh_negative_recipients_never_receive_rh_positive_cells() -> None:
    """The Rh rule holds for every Rh-negative recipient."""
    for recipient, donors in RED_CELL_COMPATIBILITY.items():
        if _is_rh_negative(recipient):
            assert all(_is_rh_negative(donor) for donor in donors)


def test_ab_negative_matches_the_published_chart() -> None:
    """AB-negative accepts exactly the four Rh-negative groups."""
    assert set(RED_CELL_COMPATIBILITY[BloodGroup.AB_NEGATIVE]) == {
        BloodGroup.AB_NEGATIVE,
        BloodGroup.A_NEGATIVE,
        BloodGroup.B_NEGATIVE,
        BloodGroup.O_NEGATIVE,
    }


def test_total_number_of_compatible_pairs() -> None:
    """The chart contains the expected 27 recipient/donor pairings."""
    assert sum(len(donors) for donors in RED_CELL_COMPATIBILITY.values()) == 27


def test_no_duplicate_donor_groups_per_recipient() -> None:
    """Each recipient lists a donor group at most once."""
    for donors in RED_CELL_COMPATIBILITY.values():
        assert len(donors) == len(set(donors))


def test_component_codes_are_unique_and_intervals_positive() -> None:
    """Component seed rows have unique codes and sensible positive intervals."""
    codes = [component["code"] for component in COMPONENT_TYPES]
    assert len(codes) == len(set(codes))
    for component in COMPONENT_TYPES:
        assert int(component["min_interval_days_male"]) > 0
        assert int(component["min_interval_days_female"]) > 0
