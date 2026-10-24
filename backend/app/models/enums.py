"""Controlled vocabularies shared by the persistence and API layers.

Each enumeration is stored in the database as a short string guarded by a CHECK
constraint (see ``base.enum_column_type``) rather than as a native PostgreSQL ENUM.
Adding a member later therefore only requires replacing a constraint, which avoids the
well-known difficulty of altering native enum types inside a transaction.
"""

from enum import StrEnum


class UserRole(StrEnum):
    """Authorisation role attached to every account."""

    DONOR = "donor"
    HOSPITAL_STAFF = "hospital_staff"
    ADMIN = "admin"


class BloodGroup(StrEnum):
    """ABO and Rh blood group. Values are the conventional written forms."""

    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"


class Sex(StrEnum):
    """Biological sex as it relates to donation intervals and haemoglobin thresholds."""

    MALE = "male"
    FEMALE = "female"


class VerificationStatus(StrEnum):
    """Outcome of the administrative review of a hospital registration.

    Only hospitals in the ``VERIFIED`` state may raise blood requests. This gate is what
    allows donors to trust that every alert originates from a real facility.
    """

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class RequestUrgency(StrEnum):
    """How quickly the hospital needs the blood."""

    CRITICAL = "critical"
    URGENT = "urgent"
    ROUTINE = "routine"


class RequestStatus(StrEnum):
    """Lifecycle of a blood request: OPEN -> FULFILLED -> CLOSED, or OPEN -> EXPIRED."""

    OPEN = "open"
    FULFILLED = "fulfilled"
    CLOSED = "closed"
    EXPIRED = "expired"


class PledgeStatus(StrEnum):
    """State of a single donor's commitment to a request.

    ``STANDBY`` is a donor waiting in reserve after every unit has been pledged; they are
    promoted to ``PLEDGED`` if a pledged donor cannot give. ``DEFERRED`` means the donor
    came but was turned away at screening. ``RELEASED`` means a standby donor was not
    needed, because the request was met or ended.
    """

    PLEDGED = "pledged"
    STANDBY = "standby"
    DONATED = "donated"
    NO_SHOW = "no_show"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"
    RELEASED = "released"


class DeferralReason(StrEnum):
    """Why a donor was turned away at screening, recorded as a category only.

    No clinical detail or test result is stored: the category sets how long the donor is
    deferred, and the donor is told to contact the hospital for anything more.
    """

    LOW_HAEMOGLOBIN = "low_haemoglobin"
    BLOOD_PRESSURE = "blood_pressure"
    RECENT_ILLNESS = "recent_illness"
    MEDICATION = "medication"
    POSITIVE_SCREEN = "positive_screen"
    OTHER = "other"


class NotificationChannel(StrEnum):
    """Delivery channel used to alert a donor."""

    SMS = "sms"
    WHATSAPP = "whatsapp"
    VOICE = "voice"


class NotificationStatus(StrEnum):
    """Delivery state of an alert."""

    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class FamilyRequestStatus(StrEnum):
    """Where a family's appeal for blood stands with the hospital it was sent to.

    A family's appeal never reaches donors by itself. It waits as ``pending`` until the
    hospital confirms the patient is really there and needs blood; ``approved`` means the
    hospital raised a blood request from it, ``declined`` that the hospital turned it down.
    """

    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
