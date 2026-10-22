"""ScannerService — QR scan processing for attendance and kit distribution.

Implements the two main scanner flows:
  - Attendance marking (with team-lock enforcement)
  - Kit issuing (idempotent)

All operations are logged to RegistrationOperation for audit and
offline-sync deduplication.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shackles.config import settings
from shackles.errors import (
    EVENT_NOT_FOUND,
    NOT_REGISTERED,
    TEAM_LOCKED,
    USER_NOT_FOUND,
    DomainError,
)
from shackles.models.enums import (
    KitStatus,
    RegistrationOperationType,
    RegistrationSyncStatus,
)
from shackles.repositories.event_registration_repo import (
    EventRegistrationRepository,
)
from shackles.repositories.event_repo import EventRepository
from shackles.repositories.registration_operation_repo import (
    RegistrationOperationRepository,
)
from shackles.repositories.team_repo import TeamRepository
from shackles.repositories.user_repo import UserRepository
from shackles.services.qr import decode_qr_payload


class ScannerService:
    """Processes QR scans for attendance, kit, and on-spot registration."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.events = EventRepository(session)
        self.registrations = EventRegistrationRepository(session)
        self.teams = TeamRepository(session)
        self.operations = RegistrationOperationRepository(session)

    # ========================================================
    # Scan lookup
    # ========================================================

    async def decode_and_lookup(self, qr_data: str) -> dict:
        """Decode a QR payload and look up the user.

        Returns:
            {
              "user": {...},
              "registrations": [...],
              "kit_status": "PENDING" | "ISSUED",
            }

        Raises:
            DomainError if the payload is invalid or the user is missing.
        """
        try:
            payload = decode_qr_payload(qr_data)
        except ValueError as exc:
            raise DomainError("INVALID_QR", str(exc)) from exc

        if payload.get("type") != "USER":
            raise DomainError(
                "INVALID_QR",
                "Expected a USER QR code.",
            )

        # Payload's uid is the qr_token
        qr_token = payload.get("uid")
        if not qr_token:
            raise DomainError("INVALID_QR", "QR payload missing uid.")

        # Year check
        if payload.get("y") != settings.active_year:
            raise DomainError(
                "WRONG_YEAR",
                f"QR is from {payload.get('y')}, not the current year "
                f"({settings.active_year}).",
            )

        user = await self.users.get_by_qr_token(qr_token)
        if user is None:
            raise DomainError(USER_NOT_FOUND, "QR token not recognized.")

        # Payment check
        payment = await self._get_payment(user.id)
        if payment is None or payment.status != "VERIFIED":
            raise DomainError(
                "PAYMENT_NOT_VERIFIED",
                "Payment not verified for the current year.",
            )

        registrations = await self.registrations.list_by_user(
            user.id, year=settings.active_year
        )

        return {
            "user": {
                "id": str(user.id),
                "first_name": user.first_name,
                "last_name": user.last_name,
                "shackles_id": user.shackles_id,
                "email": user.email,
            },
            "registrations": [
                {
                    "event_id": str(reg.event_id),
                    "event_name": reg.event.name,
                    "attended": reg.attended,
                    "team_name": reg.team_name,
                    "member_role": reg.member_role,
                }
                for reg in registrations
            ],
            "kit_status": user.kit_status,
        }

    # ========================================================
    # Attendance
    # ========================================================

    async def mark_attendance(
        self,
        *,
        user_id: UUID,
        event_id: UUID,
        station_id: str,
        operation_id: str | None = None,
        synced_at: datetime | None = None,
    ) -> dict:
        """Mark a user as attended for a specific event.

        Raises:
            DomainError if not registered or team not locked.
        """
        # Idempotent dedup
        if operation_id and await self.operations.operation_exists(operation_id):
            existing = await self.operations.get_by_operation_id_or_raise(
                operation_id
            )
            return {
                "success": True,
                "already_processed": True,
                "status": existing.status,
            }

        registration = await self.registrations.get_by_user_and_event(
            user_id, event_id
        )
        if registration is None:
            raise DomainError(
                NOT_REGISTERED,
                "Participant is not registered for this event.",
            )

        # Enforce team lock before marking attendance
        if registration.team_id is not None:
            team = await self.teams.get(registration.team_id)
            if team is None or team.status != "LOCKED":
                raise DomainError(
                    TEAM_LOCKED,
                    "Team registration must be locked before marking attendance.",
                )

        if registration.attended:
            await self._log_operation(
                operation_id=operation_id,
                station_id=station_id,
                operation_type=RegistrationOperationType.ATTENDANCE,
                participant_id=user_id,
                event_name=registration.event.name if registration.event else None,
                status=RegistrationSyncStatus.APPLIED,
                processed_at=datetime.now(timezone.utc),
            )
            return {
                "success": True,
                "already_attended": True,
                "message": "Already marked present.",
            }

        registration.attended = True
        registration.attended_at = synced_at or datetime.now(timezone.utc)
        registration.station_id = station_id
        await self.session.flush()

        await self._log_operation(
            operation_id=operation_id,
            station_id=station_id,
            operation_type=RegistrationOperationType.ATTENDANCE,
            participant_id=user_id,
            event_name=registration.event.name if registration.event else None,
            status=RegistrationSyncStatus.APPLIED,
            processed_at=datetime.now(timezone.utc),
        )

        return {
            "success": True,
            "message": "Attendance marked.",
            "event_name": registration.event.name if registration.event else None,
        }

    # ========================================================
    # Kit issuing
    # ========================================================

    async def issue_kit(
        self,
        *,
        user_id: UUID,
        station_id: str,
        operation_id: str | None = None,
    ) -> dict:
        """Issue a kit to the user. Idempotent."""
        if operation_id and await self.operations.operation_exists(operation_id):
            return {"success": True, "already_processed": True}

        user = await self.users.get(user_id)
        if user is None:
            raise DomainError(USER_NOT_FOUND, "User not found.")

        if user.kit_status == KitStatus.ISSUED.value:
            await self._log_operation(
                operation_id=operation_id,
                station_id=station_id,
                operation_type=RegistrationOperationType.KIT,
                participant_id=user_id,
                event_name=None,
                status=RegistrationSyncStatus.APPLIED,
                processed_at=datetime.now(timezone.utc),
            )
            return {
                "success": True,
                "already_issued": True,
                "message": "Kit already issued.",
            }

        user.kit_status = KitStatus.ISSUED.value
        user.kit_issued_at = datetime.now(timezone.utc)
        user.kit_issued_by = station_id
        await self.session.flush()

        await self._log_operation(
            operation_id=operation_id,
            station_id=station_id,
            operation_type=RegistrationOperationType.KIT,
            participant_id=user_id,
            event_name=None,
            status=RegistrationSyncStatus.APPLIED,
            processed_at=datetime.now(timezone.utc),
        )

        return {
            "success": True,
            "message": f"Kit issued to {user.first_name}.",
        }

    # ========================================================
    # History
    # ========================================================

    async def list_recent_scans(
        self,
        station_id: str,
        *,
        limit: int = 20,
    ) -> list[dict]:
        """Return recent operation logs for a station."""
        ops = await self.operations.list_by_station(
            station_id, limit=limit
        )
        return [
            {
                "operation_id": op.operation_id,
                "operation_type": op.operation_type,
                "participant_id": op.participant_id,
                "event_name": op.event_name,
                "status": op.status,
                "created_at": op.created_at.isoformat(),
            }
            for op in ops
        ]

    # ========================================================
    # Helpers
    # ========================================================

    async def _log_operation(
        self,
        *,
        operation_id: str | None,
        station_id: str,
        operation_type: RegistrationOperationType,
        participant_id: UUID | None,
        event_name: str | None,
        status: RegistrationSyncStatus,
        processed_at: datetime,
    ) -> None:
        if not operation_id:
            return
        # Only log if it doesn't already exist
        if await self.operations.operation_exists(operation_id):
            return
        await self.operations.create(
            operation_id=operation_id,
            station_id=station_id,
            operation_type=operation_type.value,
            participant_id=str(participant_id) if participant_id else None,
            event_name=event_name,
            status=status.value,
            processed_at=processed_at,
        )

    async def _get_payment(self, user_id: UUID):
        from shackles.repositories.payment_repo import PaymentRepository
        return await PaymentRepository(self.session).get_by_user_id(user_id)