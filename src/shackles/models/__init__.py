"""Models package.

All models must be imported here so Alembic's autogenerate discovers them
via Base.metadata.
"""

from shackles.models.enums import (
    EventCategory,
    EventParticipationMode,
    KitStatus,
    PackageType,
    PaperSelectionStatus,
    PaymentCaptureSource,
    PaymentChannel,
    PaymentStatus,
    Permission,
    RegistrationOperationType,
    RegistrationSource,
    RegistrationSyncStatus,
    RegistrationType,
    Role,
    StaffRole,
    TeamMemberRole,
    TeamStatus,
)
from shackles.models.accommodation import Accommodation
from shackles.models.component_mark import ComponentMark
from shackles.models.contact_message import ContactMessage
from shackles.models.criteria_component import CriteriaComponent
from shackles.models.event import Event
from shackles.models.event_registration import EventRegistration
from shackles.models.event_staff_assignment import EventStaffAssignment
from shackles.models.judge_marking import JudgeMarking
from shackles.models.marking_criteria import MarkingCriteria
from shackles.models.on_spot_profile import OnSpotProfile
from shackles.models.paper_submission import PaperSubmission
from shackles.models.payment import Payment
from shackles.models.registration_operation import RegistrationOperation
from shackles.models.role_permission import RolePermission
from shackles.models.shackles_id_sequence import ShacklesIdSequence
from shackles.models.team import Team
from shackles.models.team_invite import TeamInvite
from shackles.models.team_mark import TeamMark
from shackles.models.user import User

__all__ = [
    # Models
    "User",
    "Payment",
    "Event",
    "EventRegistration",
    "Team",
    "TeamInvite",
    "EventStaffAssignment",
    "OnSpotProfile",
    "Accommodation",
    "MarkingCriteria",
    "CriteriaComponent",
    "TeamMark",
    "ComponentMark",
    "JudgeMarking",
    "PaperSubmission",
    "ShacklesIdSequence",
    "RegistrationOperation",
    "RolePermission",
    "ContactMessage",
    # Enums
    "EventCategory",
    "EventParticipationMode",
    "KitStatus",
    "PackageType",
    "PaperSelectionStatus",
    "PaymentCaptureSource",
    "PaymentChannel",
    "PaymentStatus",
    "Permission",
    "RegistrationOperationType",
    "RegistrationSource",
    "RegistrationSyncStatus",
    "RegistrationType",
    "Role",
    "StaffRole",
    "TeamMemberRole",
    "TeamStatus",
]