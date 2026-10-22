"""Scanner routes for staff — decode QR, mark attendance, issue kits."""

from uuid import UUID

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentStaff
from shackles.db.session import get_session
from shackles.services.scanner_service import ScannerService


router = APIRouter(prefix="/scanner", tags=["scanner"])


# ---- Request / response shapes --------------------------------------

class DecodeRequest(BaseModel):
    qr_data: str = Field(min_length=4, max_length=2000)


class AttendanceRequest(BaseModel):
    user_id: UUID
    event_id: UUID
    station_id: str = Field(min_length=1, max_length=100)
    operation_id: str | None = Field(default=None, max_length=200)


class KitRequest(BaseModel):
    user_id: UUID
    station_id: str = Field(min_length=1, max_length=100)
    operation_id: str | None = Field(default=None, max_length=200)


class ScannerResult(BaseModel):
    success: bool
    message: str | None = None
    already_processed: bool = False
    already_attended: bool = False
    already_issued: bool = False
    event_name: str | None = None


# ---- Endpoints ------------------------------------------------------

@router.post("/decode")
async def decode_qr(
    payload: DecodeRequest,
    staff: CurrentStaff,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Decode a QR payload and look up the user."""
    service = ScannerService(session)
    return await service.decode_and_lookup(payload.qr_data)


@router.post("/attendance", response_model=ScannerResult)
async def mark_attendance(
    payload: AttendanceRequest,
    staff: CurrentStaff,
    session: AsyncSession = Depends(get_session),
) -> ScannerResult:
    """Mark attendance for a user on a specific event."""
    service = ScannerService(session)
    result = await service.mark_attendance(
        user_id=payload.user_id,
        event_id=payload.event_id,
        station_id=payload.station_id,
        operation_id=payload.operation_id,
    )
    await session.commit()
    return ScannerResult(**result)


@router.post("/kit", response_model=ScannerResult)
async def issue_kit(
    payload: KitRequest,
    staff: CurrentStaff,
    session: AsyncSession = Depends(get_session),
) -> ScannerResult:
    """Issue a kit to a user. Idempotent per operation_id."""
    service = ScannerService(session)
    result = await service.issue_kit(
        user_id=payload.user_id,
        station_id=payload.station_id,
        operation_id=payload.operation_id,
    )
    await session.commit()
    return ScannerResult(**result)


@router.get("/history")
async def scan_history(
    station_id: str,
    staff: CurrentStaff,
    session: AsyncSession = Depends(get_session),
    limit: int = 20,
) -> list[dict]:
    """Return recent scans for a station."""
    service = ScannerService(session)
    return await service.list_recent_scans(station_id, limit=limit)