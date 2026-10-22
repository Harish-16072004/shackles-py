"""Admin payment verification routes.

On APPROVE, allocates a Shackles ID + QR token and enqueues a QR
generation job. The job creates the QR image, saves it, updates the
user record, and dispatches the payment-verified email.

Also exposes a QR regeneration endpoint so admins can re-trigger
generation if the initial job failed.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentAdmin
from shackles.config import settings
from shackles.db.session import get_session
from shackles.errors import (
    INVALID_INPUT,
    NOT_FOUND,
    DomainError,
)
from shackles.repositories.user_repo import UserRepository
from shackles.schemas.payment import PaymentRead, PaymentVerify
from shackles.services.payment_service import PaymentService
from shackles.workers.queue import enqueue_qr_generation


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["admin-payments"])


# ============================================================
# Verify / reject
# ============================================================

@router.post("/{user_id}/verify", response_model=PaymentRead)
async def verify_payment(
    user_id: UUID,
    payload: PaymentVerify,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> PaymentRead:
    """Approve or reject a user's payment.

    On APPROVE:
      1. Allocates a Shackles ID and QR token
      2. Commits the transaction
      3. Enqueues a QR generation job (best-effort — never fails the request)
    """
    service = PaymentService(session)

    if payload.action == "APPROVE":
        _, qr_data = await service.verify(user_id, payload, admin_id=admin.id)
        payment = await service.get_by_user_id(user_id)

        await session.commit()

        job_id = await enqueue_qr_generation(
            user_id=qr_data["user_id"],
            qr_token=qr_data["qr_token"],
            shackles_id=qr_data["shackles_id"],
            year=qr_data["year"],
        )
        if job_id is None:
            logger.warning(
                "[payments.verify] QR job not enqueued for user=%s. "
                "Use POST /api/admin/payments/%s/regenerate-qr to retry.",
                user_id,
                user_id,
            )
    else:
        payment = await service.reject(user_id, payload, admin_id=admin.id)
        await session.commit()

    return PaymentRead.model_validate(payment)


# ============================================================
# Regenerate QR
# ============================================================

@router.post("/{user_id}/regenerate-qr")
async def regenerate_qr(
    user_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Re-enqueue a QR generation job for a verified user.

    Useful when the original job failed (Redis was down, worker crashed,
    template was missing) or the QR image file was deleted.

    Preconditions:
      - The user exists.
      - The user's payment is VERIFIED.
      - The user has both a `shackles_id` and a `qr_token`.
    """
    user = await UserRepository(session).get(user_id)
    if user is None:
        raise DomainError(NOT_FOUND, "User not found.")

    service = PaymentService(session)
    payment = await service.get_by_user_id(user_id)
    if payment is None:
        raise DomainError(NOT_FOUND, "Payment not found for this user.")

    if payment.status != "VERIFIED":
        raise DomainError(
            INVALID_INPUT,
            f"Cannot regenerate QR — payment status is {payment.status}.",
        )

    if not user.shackles_id or not user.qr_token:
        raise DomainError(
            INVALID_INPUT,
            "User is missing shackles_id or qr_token. "
            "Verify the payment first.",
        )

    job_id = await enqueue_qr_generation(
        user_id=str(user.id),
        qr_token=user.qr_token,
        shackles_id=user.shackles_id,
        year=settings.active_year,
    )

    if job_id is None:
        raise DomainError(
            "INTERNAL_ERROR",
            "Failed to enqueue QR generation job. Check worker/Redis.",
        )

    return {
        "job_id": job_id,
        "user_id": str(user.id),
        "message": "QR generation job enqueued.",
    }


# ============================================================
# Read
# ============================================================

@router.get("/{user_id}", response_model=PaymentRead)
async def get_payment(
    user_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> PaymentRead:
    """Fetch a user's payment record."""
    service = PaymentService(session)
    payment = await service.get_by_user_id(user_id)
    return PaymentRead.model_validate(payment)