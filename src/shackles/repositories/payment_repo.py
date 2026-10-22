"""PaymentRepository — data access for Payment."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select

from shackles.errors import PAYMENT_NOT_FOUND, DomainError
from shackles.models.enums import PaymentStatus
from shackles.models.payment import Payment
from shackles.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[Payment]):
    """Data access for payments."""

    model = Payment

    # ========================================================
    # Lookups
    # ========================================================

    async def get_by_user_id(self, user_id: UUID) -> Payment | None:
        """Fetch a user's payment record (one-to-one)."""
        stmt = select(Payment).where(Payment.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id_or_raise(self, user_id: UUID) -> Payment:
        """Fetch by user ID. Raises if not found."""
        payment = await self.get_by_user_id(user_id)
        if payment is None:
            raise DomainError(
                PAYMENT_NOT_FOUND,
                f"No payment found for user {user_id}",
                {"user_id": str(user_id)},
            )
        return payment

    async def get_by_transaction_id(
        self, transaction_id: str
    ) -> Payment | None:
        """Fetch a payment by its transaction ID."""
        stmt = select(Payment).where(
            Payment.transaction_id == transaction_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ========================================================
    # Filters & stats
    # ========================================================

    async def list_by_status(
        self,
        status: PaymentStatus | str,
        *,
        year: int | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[Payment]:
        """List payments by status, optionally filtered to a year."""
        status_value = status.value if isinstance(status, PaymentStatus) else status
        stmt = select(Payment).where(Payment.status == status_value)
        if year is not None:
            stmt = stmt.where(Payment.year == year)
        stmt = stmt.order_by(Payment.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_status(
        self,
        status: PaymentStatus | str,
        *,
        year: int | None = None,
    ) -> int:
        """Count payments by status."""
        status_value = status.value if isinstance(status, PaymentStatus) else status
        stmt = (
            select(func.count())
            .select_from(Payment)
            .where(Payment.status == status_value)
        )
        if year is not None:
            stmt = stmt.where(Payment.year == year)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def sum_amount_by_status(
        self,
        status: PaymentStatus | str,
        *,
        year: int | None = None,
    ) -> int:
        """Sum payment amounts for a given status (in rupees)."""
        status_value = status.value if isinstance(status, PaymentStatus) else status
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == status_value
        )
        if year is not None:
            stmt = stmt.where(Payment.year == year)
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def list_by_capture_source(
        self,
        capture_source: str,
        *,
        status: PaymentStatus | str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[Payment]:
        """List payments by capture source (WEBSITE or ON_SPOT)."""
        stmt = select(Payment).where(Payment.capture_source == capture_source)
        if status is not None:
            status_value = status.value if isinstance(status, PaymentStatus) else status
            stmt = stmt.where(Payment.status == status_value)
        stmt = stmt.order_by(Payment.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Verification helpers
    # ========================================================

    async def is_verified(self, user_id: UUID) -> bool:
        """Check whether a user's payment is verified."""
        payment = await self.get_by_user_id(user_id)
        if payment is None:
            return False
        return payment.status == PaymentStatus.VERIFIED.value

    async def get_verified_for_year(
        self,
        user_id: UUID,
        year: int,
    ) -> Payment | None:
        """Fetch a user's verified payment for a specific year.

        Used by registration eligibility checks. Returns None if the
        user has no verified payment for that year.
        """
        stmt = select(Payment).where(
            Payment.user_id == user_id,
            Payment.status == PaymentStatus.VERIFIED.value,
            Payment.year == year,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()