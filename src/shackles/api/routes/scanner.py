"""Scanner routes for staff — decode QR, mark attendance, issue kits, on-spot profiles."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import CurrentStaff
from shackles.db.session import get_session
from shackles.errors import ALREADY_EXISTS, DomainError
from shackles.repositories.on_spot_profile_repo import OnSpotProfileRepository
from shackles.schemas.on_spot_profile import (
    OnSpotProfileCreate,
    OnSpotProfileRead,
)
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


@router.post(
    "/on-spot/{user_id}",
    response_model=OnSpotProfileRead,
    status_code=201,
)
async def create_on_spot_profile(
    user_id: UUID,
    payload: OnSpotProfileCreate,
    staff: CurrentStaff,
    session: AsyncSession = Depends(get_session),
) -> OnSpotProfileRead:
    """Record on-spot registration kiosk metadata for a participant."""
    repo = OnSpotProfileRepository(session)
    if await repo.has_profile(user_id):
        raise DomainError(
            ALREADY_EXISTS,
            "An on-spot profile already exists for this user.",
        )
    profile = await repo.create(
        user_id=user_id,
        created_by_user_id=staff.id,
        station_id=payload.station_id,
        device_id=payload.device_id,
        referral_source=payload.referral_source,
        notes=payload.notes,
    )
    await session.commit()
    return OnSpotProfileRead.model_validate(profile)


@router.get("/on-spot/{user_id}", response_model=OnSpotProfileRead)
async def get_on_spot_profile(
    user_id: UUID,
    staff: CurrentStaff,
    session: AsyncSession = Depends(get_session),
) -> OnSpotProfileRead:
    """Fetch on-spot kiosk registration metadata for a participant."""
    repo = OnSpotProfileRepository(session)
    profile = await repo.get_by_user_id_or_raise(user_id)
    return OnSpotProfileRead.model_validate(profile)