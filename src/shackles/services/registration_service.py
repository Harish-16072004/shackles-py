"""RegistrationService — individual event registrations.

Handles non-team event signups: eligibility, capacity, time-clash, and
the actual registration creation. Team flows live in TeamService.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shackles.config import settings
from shackles.errors import (
    ALREADY_REGISTERED,
    EVENT_FULL,
    EVENT_INACTIVE,
    EVENT_NOT_FOUND,
    EVENT_WRONG_YEAR,
    NO_VERIFIED_PACKAGE,
    NOT_INDIVIDUAL_EVENT,
    PACKAGE_NOT_ALLOWED,
    PAYMENT_NOT_VERIFIED,
    TIME_CLASH,
    DomainError,
)
from shackles.models.enums import EventParticipationMode, RegistrationSource
from shackles.models.event import Event
from shackles.models.event_registration import EventRegistration
from shackles.models.user import User
from shackles.repositories.event_registration_repo import (
    EventRegistrationRepository,
)
from shackles.repositories.event_repo import EventRepository
from shackles.repositories.payment_repo import PaymentRepository
from shackles.repositories.user_repo import UserRepository
from shackles.services.notifications import notify_member_joined


class RegistrationService:
    """Individual (non-team) event registrations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.events = EventRepository(session)
        self.payments = PaymentRepository(session)
        self.registrations = EventRegistrationRepository(session)

    # ========================================================
    # Public API
    # ========================================================

    async def register_individual(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> EventRegistration:
        """Register a user for an INDIVIDUAL event.

        Steps:
          1. Load and validate the event
          2. Check user has verified payment for active year
          3. Check package allows the event category
          4. Check no time clash
          5. Check capacity
          6. Create the registration

        Raises:
            DomainError with codes from errors.py for each failure.
        """
        # --- 1. Load and validate event ---
        event = await self._load_and_validate_event(event_id)

        # --- 2. User & payment eligibility ---
        user = await self._load_and_validate_user(user_id)

        # --- 3. Package eligibility ---
        await self._check_package_allows(user_id, event)

        # --- 4. Time clash ---
        await self._check_time_clash(user_id, event)

        # --- 5. Already registered ---
        if await self.registrations.is_registered(user_id, event_id):
            raise DomainError(
                ALREADY_REGISTERED,
                "You are already registered for this event.",
                {"event_id": str(event_id)},
            )

        # --- 6. Capacity ---
        await self._check_capacity(event)

        # --- 7. Create registration ---
        registration = await self.registrations.create(
            user_id=user_id,
            event_id=event.id,
            team_size=1,
            source=RegistrationSource.ONLINE.value,
            sync_status="APPLIED",
            year=settings.active_year,
        )

        # --- Notify (stub) ---
        await notify_member_joined(
            member_email=user.email,
            member_name=f"{user.first_name} {user.last_name}".strip(),
            team_name="",
            event_name=event.name,
            leader_name="",
        )

        return registration

    # ========================================================
    # Public reads
    # ========================================================

    async def list_my_registrations(
        self,
        user_id: UUID,
    ) -> list[EventRegistration]:
        """List all of a user's event registrations for the active year."""
        return await self.registrations.list_by_user(
            user_id, year=settings.active_year
        )

    async def is_registered(
        self,
        user_id: UUID,
        event_id: UUID,
    ) -> bool:
        """Public check used by the UI to show 'Registered ✓' badges."""
        return await self.registrations.is_registered(user_id, event_id)

    # ========================================================
    # Private helpers
    # ========================================================

    async def _load_and_validate_event(self, event_id: UUID) -> Event:
        """Fetch an event and validate it's open for registration."""
        event = await self.events.get(event_id)
        if event is None:
            raise DomainError(
                EVENT_NOT_FOUND,
                "Event not found.",
                {"event_id": str(event_id)},
            )

        if event.year != settings.active_year:
            raise DomainError(
                EVENT_WRONG_YEAR,
                "Event is not in the active year.",
                {"event_year": event.year},
            )

        if event.is_archived or event.is_template or not event.is_active:
            raise DomainError(
                EVENT_INACTIVE,
                "Event is not open for registration.",
                {"event_id": str(event_id)},
            )

        if event.participation_mode != EventParticipationMode.INDIVIDUAL.value:
            raise DomainError(
                NOT_INDIVIDUAL_EVENT,
                "This event requires team registration.",
                {"event_id": str(event_id)},
            )

        return event

    async def _load_and_validate_user(self, user_id: UUID) -> User:
        """Fetch a user and verify their payment is current."""
        user = await self.users.get(user_id)
        if user is None:
            raise DomainError(
                "USER_NOT_FOUND",
                "User not found.",
                {"user_id": str(user_id)},
            )

        payment = await self.payments.get_by_user_id(user_id)
        if payment is None or payment.status != "VERIFIED":
            raise DomainError(
                PAYMENT_NOT_VERIFIED,
                "Payment must be verified before registering.",
                {"user_id": str(user_id)},
            )

        if payment.year != settings.active_year:
            raise DomainError(
                PAYMENT_NOT_VERIFIED,
                "Payment is not valid for the current year.",
                {"payment_year": payment.year},
            )

        return user

    async def _check_package_allows(
        self,
        user_id: UUID,
        event: Event,
    ) -> None:
        """Check that the user's package permits this event category."""
        payment = await self.payments.get_by_user_id(user_id)
        if payment is None or payment.package_type is None:
            raise DomainError(
                NO_VERIFIED_PACKAGE,
                "No verified package found for this year.",
                {"user_id": str(user_id)},
            )

        if not _package_allows_category(
            payment.package_type, event.category
        ):
            raise DomainError(
                PACKAGE_NOT_ALLOWED,
                f"Your package does not allow registering for "
                f"{event.category or 'this'} events.",
                {
                    "package_type": payment.package_type,
                    "event_category": event.category,
                },
            )

    async def _check_time_clash(
        self,
        user_id: UUID,
        new_event: Event,
    ) -> None:
        """Reject if any existing registration overlaps in time."""
        # All-day events never clash
        if new_event.is_all_day or new_event.date is None:
            return
        if new_event.end_date is None:
            return

        existing = await self.registrations.list_by_user(
            user_id, year=settings.active_year
        )

        for reg in existing:
            e = reg.event
            if e.is_all_day or e.date is None or e.end_date is None:
                continue
            # Overlap test: new.start < existing.end AND new.end > existing.start
            if new_event.date < e.end_date and new_event.end_date > e.date:
                raise DomainError(
                    TIME_CLASH,
                    f"Time conflict with '{e.name}'. You are already "
                    f"registered for an event at this time.",
                    {
                        "conflicting_event_id": str(e.id),
                        "conflicting_event_name": e.name,
                    },
                )

    async def _check_capacity(self, event: Event) -> None:
        """Reject if the event has hit its participant limit."""
        if event.max_participants is None:
            return

        current = await self.registrations.count_participants_for_event(
            event.id
        )
        if current + 1 > event.max_participants:
            raise DomainError(
                EVENT_FULL,
                "Event has reached maximum capacity.",
                {
                    "max_participants": event.max_participants,
                    "current": current,
                },
            )


# ============================================================
# Pure helpers
# ============================================================

def _package_allows_category(
    package_type: str | None,
    category: str | None,
) -> bool:
    """Return True if the package permits registration for the category.

    Mirrors the Node.js `canAccessEventCategory` logic.
    """
    if category is None:
        return True

    if package_type == "COMBO":
        return True
    if package_type == "EVENT_ONLY":
        return category == "EVENT"
    if package_type == "WORKSHOP_ONLY":
        return category == "WORKSHOP"
    return False