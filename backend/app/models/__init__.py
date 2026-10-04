"""Persistent models.

Importing this package registers every table on ``SQLModel.metadata``. The migration
environment and the test suite import it for that side effect, so a newly added model
must be exported here to be visible to schema generation.
"""

from app.models.audit_log import AuditLog
from app.models.blood_compatibility import BloodCompatibility
from app.models.blood_request import BloodRequest
from app.models.component_type import ComponentType
from app.models.donation import Donation
from app.models.donor import Donor
from app.models.donor_deferral import DonorDeferral
from app.models.hospital import Hospital
from app.models.notification import Notification
from app.models.pledge import Pledge
from app.models.user import User

__all__ = [
    "AuditLog",
    "BloodCompatibility",
    "BloodRequest",
    "ComponentType",
    "Donation",
    "Donor",
    "DonorDeferral",
    "Hospital",
    "Notification",
    "Pledge",
    "User",
]
