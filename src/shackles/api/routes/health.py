"""Health check endpoint."""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import text

from shackles.config import settings
from shackles.db.engine import engine


router = APIRouter(tags=["meta"])


@router.get("/health")
async def health() -> dict:
    """Liveness + readiness probe.

    Returns 200 with a `status` field of "healthy" or "degraded".
    """
    db_status = "ok"
    db_error: str | None = None
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = "error"
        db_error = str(exc).split("\n")[0]

    is_healthy = db_status == "ok"
    return {
        "status": "healthy" if is_healthy else "degraded",
        "checks": {
            "db": {"status": db_status, "error": db_error},
        },
        "environment": settings.environment,
        "active_year": settings.active_year,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }