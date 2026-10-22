"""Admin dashboard stats."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentAdmin
from shackles.config import settings
from shackles.db.session import get_session
from shackles.models.accommodation import Accommodation
from shackles.models.contact_message import ContactMessage
from shackles.models.enums import KitStatus, PaymentStatus, Role
from shackles.models.payment import Payment
from shackles.models.user import User
from shackles.services.event_service import EventService


router = APIRouter(prefix="/dashboard", tags=["admin"])


@router.get("/stats")
async def dashboard_stats(
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Overview counts for the admin dashboard."""
    total_users = await session.scalar(
        select(func.count()).select_from(User)
    ) or 0

    total_registered = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.role == Role.PARTICIPANT.value)
    ) or 0

    verified_payments = await session.scalar(
        select(func.count())
        .select_from(Payment)
        .where(Payment.status == PaymentStatus.VERIFIED.value)
    ) or 0

    pending_payments = await session.scalar(
        select(func.count())
        .select_from(Payment)
        .where(Payment.status == PaymentStatus.PENDING.value)
    ) or 0

    kits_issued = await session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.kit_status == KitStatus.ISSUED.value)
    ) or 0

    total_accommodations = await session.scalar(
        select(func.count()).select_from(Accommodation)
    ) or 0

    total_messages = await session.scalar(
        select(func.count()).select_from(ContactMessage)
    ) or 0

    return {
        "active_year": settings.active_year,
        "total_users": total_users,
        "total_registered_participants": total_registered,
        "verified_payments": verified_payments,
        "pending_payments": pending_payments,
        "kits_issued": kits_issued,
        "total_accommodations": total_accommodations,
        "total_contact_messages": total_messages,
    }


@router.get("/events/{event_id}/stats")
async def event_stats(
    event_id: UUID,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Per-event registration + attendance stats."""
    service = EventService(session)
    return await service.get_event_stats(event_id)