"""Admin CSV exports.

All exports return a StreamingResponse with text/csv. Currently they
load rows synchronously; a later phase moves them to ARQ jobs.
"""

import csv
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentAdmin
from shackles.config import settings
from shackles.db.session import get_session
from shackles.models.accommodation import Accommodation
from shackles.models.event_registration import EventRegistration
from shackles.models.payment import Payment
from shackles.models.user import User
from sqlalchemy import select
from sqlalchemy.orm import selectinload


router = APIRouter(prefix="/exports", tags=["admin-exports"])


def _csv_response(rows: list[list], headers: list[str], filename: str) -> StreamingResponse:
    """Build a streaming CSV response."""
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/payments")
async def export_payments(
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
    status: str | None = Query(default=None),
) -> StreamingResponse:
    """Export payments as CSV."""
    stmt = select(Payment).options(selectinload(Payment.user))
    if status:
        stmt = stmt.where(Payment.status == status.upper())
    stmt = stmt.order_by(Payment.created_at.desc())
    result = await session.execute(stmt)
    payments = result.scalars().all()

    rows = [
        [
            f"{p.user.first_name} {p.user.last_name}" if p.user else "",
            p.user.email if p.user else "",
            p.user.phone if p.user else "",
            p.amount,
            p.transaction_id,
            p.status,
            p.payment_channel,
            p.capture_source,
            p.year or "",
            p.verified_at.isoformat() if p.verified_at else "",
            p.created_at.isoformat(),
        ]
        for p in payments
    ]
    headers = [
        "Name", "Email", "Phone", "Amount", "Transaction ID",
        "Status", "Channel", "Capture Source", "Year",
        "Verified At", "Created At",
    ]
    return _csv_response(
        rows, headers, f"payments-{settings.active_year}.csv"
    )


@router.get("/registrations")
async def export_registrations(
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
    event_id: UUID | None = Query(default=None),
) -> StreamingResponse:
    """Export event registrations as CSV."""
    stmt = (
        select(EventRegistration)
        .options(
            selectinload(EventRegistration.user),
            selectinload(EventRegistration.event),
        )
        .order_by(EventRegistration.created_at.desc())
    )
    if event_id:
        stmt = stmt.where(EventRegistration.event_id == event_id)
    else:
        stmt = stmt.where(EventRegistration.year == settings.active_year)

    result = await session.execute(stmt)
    regs = result.scalars().all()

    rows = [
        [
            r.event.name if r.event else "",
            r.user.first_name if r.user else "",
            r.user.last_name if r.user else "",
            r.user.email if r.user else "",
            r.user.phone if r.user else "",
            r.user.shackles_id if r.user else "",
            r.team_name or "",
            r.member_role or "",
            "YES" if r.attended else "NO",
            r.attended_at.isoformat() if r.attended_at else "",
            r.source,
        ]
        for r in regs
    ]
    headers = [
        "Event", "First Name", "Last Name", "Email", "Phone",
        "Shackles ID", "Team", "Role", "Attended", "Attended At", "Source",
    ]
    return _csv_response(
        rows, headers, f"registrations-{settings.active_year}.csv"
    )


@router.get("/accommodations")
async def export_accommodations(
    admin: CurrentAdmin,
    session: AsyncSession = Depends(get_session),
    gender: str = Query(pattern="^(MALE|FEMALE)$"),
) -> StreamingResponse:
    """Export accommodation requests filtered by gender."""
    stmt = (
        select(Accommodation)
        .join(User, Accommodation.user_id == User.id)
        .where(User.gender == gender)
        .options(selectinload(Accommodation.user))
        .order_by(Accommodation.created_at.desc())
    )
    result = await session.execute(stmt)
    accs = result.scalars().all()

    rows = [
        [
            a.user.first_name if a.user else "",
            a.user.last_name if a.user else "",
            a.user.email if a.user else "",
            a.user.phone if a.user else "",
            a.user.college_name if a.user else "",
            "; ".join(a.days),
            a.created_at.isoformat(),
        ]
        for a in accs
    ]
    headers = ["First Name", "Last Name", "Email", "Phone", "College", "Days", "Created"]
    return _csv_response(
        rows, headers, f"accommodations-{gender.lower()}-{settings.active_year}.csv"
    )