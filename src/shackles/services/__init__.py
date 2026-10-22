"""Services package — business logic layer.

Services orchestrate repositories, enforce business rules, and raise
DomainError on violations. They do NOT commit transactions — the API
layer owns the transaction boundary.
"""

from shackles.services.auth_service import AuthService
from shackles.services.event_service import EventService
from shackles.services.marking_service import MarkingService
from shackles.services.paper_submission_service import PaperSubmissionService
from shackles.services.payment_service import PaymentService
from shackles.services.registration_service import RegistrationService
from shackles.services.scanner_service import ScannerService
from shackles.services.team_service import TeamService
from shackles.services.user_service import UserService

__all__ = [
    "AuthService",
    "UserService",
    "PaymentService",
    "EventService",
    "RegistrationService",
    "TeamService",
    "MarkingService",
    "PaperSubmissionService",
    "ScannerService",
]