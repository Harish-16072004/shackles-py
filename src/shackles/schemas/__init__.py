"""Schemas package — Pydantic models for API I/O."""

from shackles.schemas.accommodation import (
    AccommodationCreate,
    AccommodationRead,
)
from shackles.schemas.common import (
    ApiBase,
    ApiRead,
    ApiWrite,
    ErrorResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
    normalize_phone,
    validate_password_strength,
)
from shackles.schemas.contact_message import (
    ContactMessageCreate,
    ContactMessageRead,
)
from shackles.schemas.event import (
    EventCreate,
    EventListFilters,
    EventRead,
    EventUpdate,
)
from shackles.schemas.event_registration import (
    AttendanceMark,
    EventRegistrationCreate,
    EventRegistrationRead,
    EventRegistrationWithUser,
)
from shackles.schemas.event_staff_assignment import (
    StaffAssignmentCreate,
    StaffAssignmentRead,
    StaffUserCreate,
)
from shackles.schemas.marking import (
    BulkMarksSubmit,
    CriteriaComponentCreate,
    CriteriaComponentRead,
    JudgeMarkingCreate,
    JudgeMarkingRead,
    LeaderboardEntry,
    LeaderboardResponse,
    MarkingCriteriaCreate,
    MarkingCriteriaRead,
    TeamMarkRead,
    TeamMarkWithTeam,
    TeamMarksSubmission,
)
from shackles.schemas.on_spot_profile import (
    OnSpotProfileCreate,
    OnSpotProfileRead,
)
from shackles.schemas.paper_submission import (
    DeadlineUpdate,
    PaperSelectionUpdate,
    PaperSubmissionRead,
)
from shackles.schemas.payment import (
    PaymentCreate,
    PaymentRead,
    PaymentVerify,
)
from shackles.schemas.registration_operation import (
    RegistrationOperationCreate,
    RegistrationOperationRead,
)
from shackles.schemas.role_permission import (
    RolePermissionCreate,
    RolePermissionMatrix,
    RolePermissionRead,
)
from shackles.schemas.team import (
    TeamBulkRegister,
    TeamCreate,
    TeamDetailRead,
    TeamJoin,
    TeamJoinWithInvite,
    TeamLockRequest,
    TeamMemberRead,
    TeamRead,
)
from shackles.schemas.team_invite import (
    TeamInviteCreate,
    TeamInviteRead,
)
from shackles.schemas.user import (
    UserCreate,
    UserLogin,
    UserPasswordChange,
    UserRead,
    UserReadWithQR,
    UserRoleUpdate,
    UserUpdate,
)

__all__ = [
    # Common
    "ApiBase",
    "ApiRead",
    "ApiWrite",
    "ErrorResponse",
    "MessageResponse",
    "PaginatedResponse",
    "PaginationParams",
    "normalize_phone",
    "validate_password_strength",
    # User
    "UserCreate",
    "UserLogin",
    "UserPasswordChange",
    "UserRead",
    "UserReadWithQR",
    "UserRoleUpdate",
    "UserUpdate",
    # Payment
    "PaymentCreate",
    "PaymentRead",
    "PaymentVerify",
    # Event
    "EventCreate",
    "EventListFilters",
    "EventRead",
    "EventUpdate",
    # EventRegistration
    "AttendanceMark",
    "EventRegistrationCreate",
    "EventRegistrationRead",
    "EventRegistrationWithUser",
    # Team
    "TeamBulkRegister",
    "TeamCreate",
    "TeamDetailRead",
    "TeamJoin",
    "TeamJoinWithInvite",
    "TeamLockRequest",
    "TeamMemberRead",
    "TeamRead",
    # TeamInvite
    "TeamInviteCreate",
    "TeamInviteRead",
    # Staff
    "StaffAssignmentCreate",
    "StaffAssignmentRead",
    "StaffUserCreate",
    # OnSpotProfile
    "OnSpotProfileCreate",
    "OnSpotProfileRead",
    # Accommodation
    "AccommodationCreate",
    "AccommodationRead",
    # Marking
    "BulkMarksSubmit",
    "CriteriaComponentCreate",
    "CriteriaComponentRead",
    "JudgeMarkingCreate",
    "JudgeMarkingRead",
    "LeaderboardEntry",
    "LeaderboardResponse",
    "MarkingCriteriaCreate",
    "MarkingCriteriaRead",
    "TeamMarkRead",
    "TeamMarkWithTeam",
    "TeamMarksSubmission",
    # PaperSubmission
    "DeadlineUpdate",
    "PaperSelectionUpdate",
    "PaperSubmissionRead",
    # RegistrationOperation
    "RegistrationOperationCreate",
    "RegistrationOperationRead",
    # RolePermission
    "RolePermissionCreate",
    "RolePermissionMatrix",
    "RolePermissionRead",
    # Contact
    "ContactMessageCreate",
    "ContactMessageRead",
]