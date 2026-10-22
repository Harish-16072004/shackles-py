"""Repositories package — data access layer.

Repositories wrap SQLAlchemy queries behind a clean interface. Services
depend on repositories, not on SQLAlchemy directly.
"""

from shackles.repositories.accommodation_repo import AccommodationRepository
from shackles.repositories.base import BaseRepository
from shackles.repositories.contact_message_repo import (
    ContactMessageRepository,
)
from shackles.repositories.event_registration_repo import (
    EventRegistrationRepository,
)
from shackles.repositories.event_repo import EventRepository
from shackles.repositories.event_staff_assignment_repo import (
    EventStaffAssignmentRepository,
)
from shackles.repositories.marking_repo import (
    ComponentMarkRepository,
    CriteriaComponentRepository,
    JudgeMarkingRepository,
    MarkingCriteriaRepository,
    TeamMarkRepository,
)
from shackles.repositories.on_spot_profile_repo import (
    OnSpotProfileRepository,
)
from shackles.repositories.paper_submission_repo import (
    PaperSubmissionRepository,
)
from shackles.repositories.payment_repo import PaymentRepository
from shackles.repositories.registration_operation_repo import (
    RegistrationOperationRepository,
)
from shackles.repositories.role_permission_repo import (
    RolePermissionRepository,
)
from shackles.repositories.team_invite_repo import TeamInviteRepository
from shackles.repositories.team_repo import TeamRepository
from shackles.repositories.user_repo import UserRepository

__all__ = [
    # Base
    "BaseRepository",
    # Users & access
    "UserRepository",
    "RolePermissionRepository",
    # Events & registration
    "EventRepository",
    "EventRegistrationRepository",
    "EventStaffAssignmentRepository",
    # Teams
    "TeamRepository",
    "TeamInviteRepository",
    # Payments
    "PaymentRepository",
    # On-spot
    "OnSpotProfileRepository",
    # Accommodation
    "AccommodationRepository",
    # Contact
    "ContactMessageRepository",
    # Scanner operations
    "RegistrationOperationRepository",
    # Marking
    "MarkingCriteriaRepository",
    "CriteriaComponentRepository",
    "TeamMarkRepository",
    "ComponentMarkRepository",
    "JudgeMarkingRepository",
    # Paper submission
    "PaperSubmissionRepository",
]