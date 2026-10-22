"""Admin ID card PDF export — real A3 composition."""

from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentAdmin
from shackles.config import settings
from shackles.db.session import get_session
from shackles.models.user import User
from shackles.services.id_cards import build_a3_pdf, compose_card


router = APIRouter(prefix="/id-cards", tags=["admin-id-cards"])


_VALID_TYPES = {"GENERAL", "WORKSHOP", "COMBO", "ALL"}


@router.get("/{reg_type}")
async def export_id_cards(
    reg_type: str,
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Generate an A3 PDF of ID cards.

    Args:
        reg_type: 'GENERAL', 'WORKSHOP', 'COMBO', or 'ALL'.

    Cards are laid out 4x4 per A3 page. Each card includes the user's
    Shackles ID and QR code (loaded from local storage).
    """
    reg_type_upper = reg_type.upper()
    if reg_type_upper not in _VALID_TYPES:
        from shackles.errors import INVALID_INPUT, DomainError

        raise DomainError(
            INVALID_INPUT,
            f"Invalid registration type: {reg_type}",
        )

    stmt = (
        select(User)
        .where(
            User.shackles_id.isnot(None),
            User.payment.has(status="VERIFIED"),
        )
        .order_by(User.shackles_id.asc())
    )
    if reg_type_upper != "ALL":
        stmt = stmt.where(User.registration_type == reg_type_upper)

    result = await session.execute(stmt)
    users = result.scalars().all()

    if not users:
        from shackles.errors import NOT_FOUND, DomainError

        raise DomainError(NOT_FOUND, "No eligible participants found.")

    # Compose one card per user
    cards = []
    for user in users:
        qr_bytes: bytes | None = None
        if user.qr_path:
            from pathlib import Path

            qr_absolute = Path(settings.storage_local_root) / user.qr_path
            if qr_absolute.exists():
                qr_bytes = qr_absolute.read_bytes()

        card = compose_card(user.shackles_id or "", qr_bytes)
        cards.append(card)

    pdf_bytes = build_a3_pdf(cards, title=f"{reg_type_upper} ID Cards")

    filename = (
        f"id-cards-{reg_type_upper.lower()}-{settings.active_year}.pdf"
    )
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )