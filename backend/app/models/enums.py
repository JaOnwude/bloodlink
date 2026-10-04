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
    """State of a single donor's commitment to a request."""

    PLEDGED = "pledged"
    DONATED = "donated"
    NO_SHOW = "no_show"
    CANCELLED = "cancelled"


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
