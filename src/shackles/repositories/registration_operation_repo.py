"""RegistrationOperationRepository — data access for scanner operation logs."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update

from shackles.errors import NOT_FOUND, DomainError
from shackles.models.enums import RegistrationSyncStatus
from shackles.models.registration_operation import RegistrationOperation
from shackles.repositories.base import BaseRepository


class RegistrationOperationRepository(BaseRepository[RegistrationOperation]):
    """Data access for scanner operation logs.

    Used for:
      - Auditing every scan
      - Deduplicating retries via client-supplied `operationId`
      - Replaying offline-queued operations
    """

    model = RegistrationOperation

    # ========================================================
    # Lookups
    # ========================================================

    async def get_by_operation_id(
        self,
        operation_id: str,
    ) -> RegistrationOperation | None:
        """Look up an operation by its client-supplied ID (dedup key)."""
        stmt = select(RegistrationOperation).where(
            RegistrationOperation.operation_id == operation_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_operation_id_or_raise(
        self,
        operation_id: str,
    ) -> RegistrationOperation:
        """Fetch by operation_id. Raises if not found."""
        op = await self.get_by_operation_id(operation_id)
        if op is None:
            raise DomainError(
                NOT_FOUND,
                f"Operation {operation_id} not found.",
                {"operation_id": operation_id},
            )
        return op

    async def operation_exists(self, operation_id: str) -> bool:
        """Check whether an operation has already been recorded.

        This is the dedup primitive. Offline scanners check this before
        submitting, and the server uses it to make retries idempotent.
        """
        stmt = (
            select(func.count())
            .select_from(RegistrationOperation)
            .where(RegistrationOperation.operation_id == operation_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    # ========================================================
    # Lists
    # ========================================================

    async def list_by_station(
        self,
        station_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RegistrationOperation]:
        """List operations recorded at a station, newest first."""
        stmt = (
            select(RegistrationOperation)
            .where(RegistrationOperation.station_id == station_id)
            .order_by(RegistrationOperation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_sync(
        self,
        station_id: str | None = None,
        *,
        limit: int = 500,
    ) -> list[RegistrationOperation]:
        """List operations still in PENDING state (awaiting sync).

        Used by the reconciliation job: when a station comes back online,
        it re-submits pending operations and the server applies them.
        """
        stmt = select(RegistrationOperation).where(
            RegistrationOperation.status
            == RegistrationSyncStatus.PENDING.value
        )
        if station_id is not None:
            stmt = stmt.where(RegistrationOperation.station_id == station_id)
        stmt = (
            stmt.order_by(RegistrationOperation.created_at.asc()).limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_failed(
        self,
        *,
        limit: int = 500,
    ) -> list[RegistrationOperation]:
        """List operations that failed to apply."""
        stmt = (
            select(RegistrationOperation)
            .where(
                RegistrationOperation.status
                == RegistrationSyncStatus.FAILED.value
            )
            .order_by(RegistrationOperation.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_participant(
        self,
        participant_id: UUID,
        *,
        limit: int = 50,
    ) -> list[RegistrationOperation]:
        """List all operations involving a participant (audit trail)."""
        stmt = (
            select(RegistrationOperation)
            .where(
                RegistrationOperation.participant_id == str(participant_id)
            )
            .order_by(RegistrationOperation.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Counts / stats
    # ========================================================

    async def count_by_station(self, station_id: str) -> int:
        """Total operations at a station."""
        stmt = (
            select(func.count())
            .select_from(RegistrationOperation)
            .where(RegistrationOperation.station_id == station_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_pending_sync(
        self,
        station_id: str | None = None,
    ) -> int:
        """Count operations still awaiting sync."""
        stmt = (
            select(func.count())
            .select_from(RegistrationOperation)
            .where(
                RegistrationOperation.status
                == RegistrationSyncStatus.PENDING.value
            )
        )
        if station_id is not None:
            stmt = stmt.where(RegistrationOperation.station_id == station_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def count_by_status(
        self,
        status: RegistrationSyncStatus | str,
    ) -> int:
        """Count operations in a given sync status."""
        status_value = (
            status.value
            if isinstance(status, RegistrationSyncStatus)
            else status
        )
        stmt = (
            select(func.count())
            .select_from(RegistrationOperation)
            .where(RegistrationOperation.status == status_value)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ========================================================
    # State transitions
    # ========================================================

    async def mark_applied(
        self,
        operation_id: str,
        processed_at: datetime | None = None,
    ) -> bool:
        """Mark an operation as APPLIED. Returns True if updated.

        Only succeeds if the operation is currently PENDING. Returns
        False if the operation is missing or already processed.
        """
        ts = processed_at or datetime.now(timezone.utc)
        stmt = (
            update(RegistrationOperation)
            .where(
                RegistrationOperation.operation_id == operation_id,
                RegistrationOperation.status
                == RegistrationSyncStatus.PENDING.value,
            )
            .values(
                status=RegistrationSyncStatus.APPLIED.value,
                processed_at=ts,
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return (result.rowcount or 0) > 0

    async def mark_failed(
        self,
        operation_id: str,
        error_message: str,
    ) -> bool:
        """Mark an operation as FAILED with an error message.

        Works regardless of current status — an operation that was
        APPLIED and then discovered to have failed can be re-marked.
        """
        stmt = (
            update(RegistrationOperation)
            .where(RegistrationOperation.operation_id == operation_id)
            .values(
                status=RegistrationSyncStatus.FAILED.value,
                error_message=error_message[:1000],
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return (result.rowcount or 0) > 0