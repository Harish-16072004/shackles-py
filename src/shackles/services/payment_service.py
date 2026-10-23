"""PaymentService — create, verify, and reject payments.

Owns the flow that turns a PENDING payment into a fully-registered
participant with a Shackles ID and a QR token.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shackles.config import settings
from shackles.errors import (
    ALREADY_EXISTS,
    NOT_FOUND,
    PAYMENT_NOT_VERIFIED,
    DomainError,
)
from shackles.models.enums import (
    PaymentCaptureSource,
    PaymentStatus,
    Role,
)
from shackles.models.payment import Payment
from shackles.models.user import User
from shackles.repositories.payment_repo import PaymentRepository
from shackles.repositories.user_repo import UserRepository
from shackles.schemas.payment import PaymentCreate, PaymentVerify
from shackles.services.qr import generate_qr_token
from shackles.services.shackles_id import allocate_shackles_id


_QR_TOKEN_TTL_DAYS = 30
_ON_SPOT_SEQUENCE_START = 500


class PaymentService:
    """Payment creation and verification."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.payments = PaymentRepository(session)
        self.users = UserRepository(session)

    # ========================================================
    # Read
    # ========================================================

    async def get_by_user_id(self, user_id: UUID) -> Payment:
        """Fetch a user's payment. Raises if not found."""
        return await self.payments.get_by_user_id_or_raise(user_id)

    async def get_status(self, user_id: UUID) -> str | None:
        """Return the payment status for a user, or None."""
        payment = await self.payments.get_by_user_id(user_id)
        return payment.status if payment else None

    # ========================================================
    # Create (called from registration flows)
    # ========================================================

    async def create_for_user(
        self,
        user_id: UUID,
        data: PaymentCreate,
    ) -> Payment:
        """Create a payment record attached to the given user.

        Raises:
            DomainError(ALREADY_EXISTS) if the user already has a payment.
        """
        existing = await self.payments.get_by_user_id(user_id)
        if existing is not None:
            raise DomainError(
                ALREADY_EXISTS,
                "A payment record already exists for this user.",
                {"user_id": str(user_id)},
            )

        payment = await self.payments.create(
            user_id=user_id,
            amount=data.amount,
            transaction_id=data.transaction_id,
            proof_url=data.proof_url,
            proof_path=data.proof_path,
            payment_channel=data.payment_channel.value,
            capture_source=data.capture_source.value,
            package_type=data.package_type.value if data.package_type else None,
            year=data.year or settings.active_year,
            status=PaymentStatus.PENDING.value,
        )
        return payment

    # ========================================================
    # Verify (admin action)
    # ========================================================

    async def verify(
        self,
        user_id: UUID,
        data: PaymentVerify,
        *,
        admin_id: UUID,
    ) -> tuple[User, dict]:
        """Approve a payment: allocate Shackles ID, generate QR token.

        Returns:
            (updated_user, qr_payload_data) — the caller uses the second
            value to enqueue a QR generation job after commit (which also
            dispatches the payment-verified email with the QR image URL).

        Raises:
            DomainError(NOT_FOUND) if the payment doesn't exist.
            DomainError(PAYMENT_NOT_VERIFIED) if it's not PENDING.
        """
        payment = await self.payments.get_by_user_id(user_id)
        if payment is None:
            raise DomainError(
                NOT_FOUND,
                "Payment not found for this user.",
                {"user_id": str(user_id)},
            )

        if payment.status != PaymentStatus.PENDING.value:
            raise DomainError(
                PAYMENT_NOT_VERIFIED,
                f"Payment cannot be verified (current status: {payment.status}).",
                {"status": payment.status},
            )

        user = await self.users.get(user_id)
        if user is None:
            raise DomainError(
                NOT_FOUND,
                "User not found.",
                {"user_id": str(user_id)},
            )

        # --- Determine sequence floor based on capture source ---
        is_on_spot = payment.capture_source == PaymentCaptureSource.ON_SPOT.value
        start_from = _ON_SPOT_SEQUENCE_START if is_on_spot else 1

        # --- Allocate Shackles ID ---
        shackles_id = await allocate_shackles_id(
            self.session,
            year=settings.active_year,
            registration_type=user.registration_type,
            start_from=start_from,
        )

        # --- Generate QR token ---
        qr_token = generate_qr_token()
        qr_expiry = datetime.now(timezone.utc) + timedelta(days=_QR_TOKEN_TTL_DAYS)

        # --- Update user ---
        user.shackles_id = shackles_id
        user.qr_token = qr_token
        user.qr_token_expiry = qr_expiry
        user.qr_image_url = None
        user.qr_path = None
        user.role = Role.PARTICIPANT.value

        # --- Update payment ---
        payment.status = PaymentStatus.VERIFIED.value
        payment.verified_at = datetime.now(timezone.utc)
        payment.verified_by = str(admin_id)
        payment.verification_note = data.verification_note
        payment.year = settings.active_year

        await self.session.flush()
        await self.session.refresh(user)
        await self.session.refresh(payment)

        # --- Return QR data for the caller to enqueue post-commit ---
        qr_payload_data = {
            "user_id": str(user.id),
            "user_email": user.email,
            "user_name": f"{user.first_name} {user.last_name}".strip(),
            "qr_token": qr_token,
            "shackles_id": shackles_id,
            "registration_type": user.registration_type,
            "package_type": payment.package_type or "EVENT_ONLY",
            "year": settings.active_year,
        }

        return user, qr_payload_data

    # ========================================================
    # Reject (admin action)
    # ========================================================

    async def reject(
        self,
        user_id: UUID,
        data: PaymentVerify,
        *,
        admin_id: UUID,
    ) -> Payment:
        """Reject a payment with a reason."""
        payment = await self.payments.get_by_user_id(user_id)
        if payment is None:
            raise DomainError(
                NOT_FOUND,
                "Payment not found.",
                {"user_id": str(user_id)},
            )

        if payment.status == PaymentStatus.VERIFIED.value:
            raise DomainError(
                PAYMENT_NOT_VERIFIED,
                "Cannot reject a payment that is already verified.",
            )

        payment.status = PaymentStatus.REJECTED.value
        payment.rejected_at = datetime.now(timezone.utc)
        payment.rejection_reason = data.rejection_reason
        payment.verification_note = data.verification_note
        payment.verified_by = str(admin_id)

        await self.session.flush()
        await self.session.refresh(payment)
        return payment

    # ========================================================
    # Helpers
    # ========================================================

    async def is_verified_for_year(
        self,
        user_id: UUID,
        year: int | None = None,
    ) -> bool:
        """Check whether a user has a verified payment for a year."""
        target_year = year or settings.active_year
        payment = await self.payments.get_verified_for_year(user_id, target_year)
        return payment is not None