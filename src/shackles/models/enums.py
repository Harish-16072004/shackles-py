"""Python enums matching the Prisma schema."""

import enum


class Role(str, enum.Enum):
    """User roles. Values match the Node app's string representation."""

    APPLICANT = "APPLICANT"
    PARTICIPANT = "PARTICIPANT"
    VOLUNTEER = "VOLUNTEER"
    ADMIN = "ADMIN"
    COORDINATOR = "COORDINATOR"


class RegistrationType(str, enum.Enum):
    """Pass type purchased at registration."""

    GENERAL = "GENERAL"
    WORKSHOP = "WORKSHOP"
    COMBO = "COMBO"


class PackageType(str, enum.Enum):
    """What a payment allows access to."""

    EVENT_ONLY = "EVENT_ONLY"
    WORKSHOP_ONLY = "WORKSHOP_ONLY"
    COMBO = "COMBO"


class KitStatus(str, enum.Enum):
    """Whether the participant has collected their kit."""

    PENDING = "PENDING"
    ISSUED = "ISSUED"


class PaymentStatus(str, enum.Enum):
    """Payment verification state."""

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class PaymentChannel(str, enum.Enum):
    """How the payment was made."""

    ONLINE = "ONLINE"
    CASH = "CASH"


class PaymentCaptureSource(str, enum.Enum):
    """Where the payment was captured from."""

    WEBSITE = "WEBSITE"
    ON_SPOT = "ON_SPOT"


class EventCategory(str, enum.Enum):
    """Event category (top-level filter)."""

    EVENT = "EVENT"
    WORKSHOP = "WORKSHOP"


class EventParticipationMode(str, enum.Enum):
    """How participants join an event."""

    INDIVIDUAL = "INDIVIDUAL"
    TEAM = "TEAM"


class TeamStatus(str, enum.Enum):
    """Lifecycle state of a team."""

    OPEN = "OPEN"
    DRAFT = "DRAFT"
    LOCKED = "LOCKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TeamMemberRole(str, enum.Enum):
    """A member's role within a team."""

    LEADER = "LEADER"
    MEMBER = "MEMBER"


class RegistrationSource(str, enum.Enum):
    """How a registration was created."""

    ONLINE = "ONLINE"
    ON_SPOT = "ON_SPOT"
    CSV_IMPORT = "CSV_IMPORT"


class RegistrationSyncStatus(str, enum.Enum):
    """Sync state for offline-capable registrations."""

    PENDING = "PENDING"
    APPLIED = "APPLIED"
    CONFLICT = "CONFLICT"
    FAILED = "FAILED"


class StaffRole(str, enum.Enum):
    """Role a staff member plays for an event."""

    COORDINATOR = "COORDINATOR"
    VOLUNTEER = "VOLUNTEER"


class PaperSelectionStatus(str, enum.Enum):
    """Status of a paper abstract selection."""

    PENDING = "PENDING"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"


class Permission(str, enum.Enum):
    """Fine-grained permissions."""

    SCAN_ATTENDANCE = "SCAN_ATTENDANCE"
    SCAN_KIT = "SCAN_KIT"
    ONSPOT_INDIVIDUAL_REG = "ONSPOT_INDIVIDUAL_REG"
    ONSPOT_TEAM_REG = "ONSPOT_TEAM_REG"
    MANAGE_TEAMS = "MANAGE_TEAMS"
    MANAGE_SCORES = "MANAGE_SCORES"
    MANAGE_SUBMISSIONS = "MANAGE_SUBMISSIONS" 

class RegistrationOperationType(str, enum.Enum):
    """Type of scanner operation recorded for audit / sync replay."""

    KIT = "KIT"
    ATTENDANCE = "ATTENDANCE"
    QUICK_REGISTER = "QUICK_REGISTER"
    TEAM_ADD = "TEAM_ADD"
    TEAM_COMPLETE = "TEAM_COMPLETE"