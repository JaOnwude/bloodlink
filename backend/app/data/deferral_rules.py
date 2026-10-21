"""How long a donor is deferred after being turned away at screening, by reason.

When hospital staff record that a donor came but could not give, they choose a reason
category, and the donor is deferred for the period below. The rules live here, in one
place, so they can be reviewed by clinical staff and changed without touching the pledge
logic.

IMPORTANT: the periods are PLACEHOLDERS so the system can run end to end. They must be
replaced with the figures used by the hospital's blood bank and the national blood service,
cited in the project research notes, before the platform is used beyond demonstration.

A period of ``None`` is a permanent deferral. A positive infection screen is handled that
way: the donor is never told the result through BloodLink, only asked to contact the
hospital, which informs them in person and refers them for care.
"""

from dataclasses import dataclass

from app.models.enums import DeferralReason


@dataclass(frozen=True)
class DeferralRule:
    """What happens to a donor deferred for one reason.

    Attributes:
        days: How long the deferral lasts, or None for permanently.
        staff_label: What hospital staff choose from, written to be unambiguous to them.
        label: The reason as stored on the donor's deferral record. Kept neutral, because
            the record travels with the donor to every hospital that checks eligibility.
        donor_message: What the donor is told. Never contains a test result.
    """

    days: int | None
    staff_label: str
    label: str
    donor_message: str


DEFERRAL_RULES: dict[DeferralReason, DeferralRule] = {
    DeferralReason.LOW_HAEMOGLOBIN: DeferralRule(
        days=90,
        staff_label="Low haemoglobin",
        label="Low haemoglobin at screening",
        donor_message=(
            "Your haemoglobin was a little low on the day. Eat iron-rich food and you can "
            "try again after the date shown."
        ),
    ),
    DeferralReason.BLOOD_PRESSURE: DeferralRule(
        days=7,
        staff_label="Blood pressure out of range",
        label="Blood pressure outside the range for donation",
        donor_message="Your blood pressure was outside the range for donating on the day.",
    ),
    DeferralReason.RECENT_ILLNESS: DeferralRule(
        days=14,
        staff_label="Recent illness",
        label="Recent illness",
        donor_message="You can give again once you have fully recovered.",
    ),
    DeferralReason.MEDICATION: DeferralRule(
        days=28,
        staff_label="Current medication",
        label="Current medication",
        donor_message="A medicine you are taking means you should wait before giving.",
    ),
    DeferralReason.POSITIVE_SCREEN: DeferralRule(
        days=None,
        staff_label="Positive infection screen (HIV, hepatitis B or C, syphilis)",
        label="Deferred after screening",
        donor_message=(
            "Please contact the hospital about your screening. They will speak with you in "
            "confidence."
        ),
    ),
    DeferralReason.OTHER: DeferralRule(
        days=30,
        staff_label="Other reason",
        label="Deferred at screening",
        donor_message="The hospital could not take your donation this time.",
    ),
}
