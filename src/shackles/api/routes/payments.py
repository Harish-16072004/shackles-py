"""Payment proof upload route."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel

from shackles.api.deps import CurrentUser
from shackles.config import settings
from shackles.errors import INVALID_INPUT, DomainError
from shackles.services.rate_limit import LIMIT_UPLOAD, limiter


router = APIRouter(prefix="/payments", tags=["payments"])


_MAX_BYTES = 4 * 1024 * 1024
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class ProofUploadResponse(BaseModel):
    proof_path: str
    proof_url: str


def _infer_extension(upload: UploadFile) -> str:
    ctype = (upload.content_type or "").lower()
    if "png" in ctype:
        return "png"
    if "webp" in ctype:
        return "webp"
    if "gif" in ctype:
        return "gif"
    name = (upload.filename or "").lower()
    for ext in ("png", "webp", "gif", "jpg", "jpeg"):
        if name.endswith("." + ext):
            return "jpg" if ext == "jpeg" else ext
    return "jpg"


@router.post("/upload-proof", response_model=ProofUploadResponse)
@limiter.limit(LIMIT_UPLOAD)
async def upload_payment_proof(
    request: Request,
    user: CurrentUser,
    file: UploadFile = File(...),
) -> ProofUploadResponse:
    """Store an uploaded payment proof image.

    The file lands under `{storage_local_root}/payment-proofs/`.
    Serving is handled by the `/static` mount in main.py.
    """
    if file.content_type not in _ALLOWED_TYPES:
        raise DomainError(
            INVALID_INPUT,
            f"Unsupported file type: {file.content_type}",
        )

    body = await file.read()
    if len(body) > _MAX_BYTES:
        raise DomainError(
            INVALID_INPUT,
            f"File too large (max {_MAX_BYTES // 1024 // 1024} MB).",
        )

    ext = _infer_extension(file)
    filename = f"{uuid.uuid4().hex}.{ext}"
    storage_key = f"payment-proofs/{settings.active_year}/{user.id}/{filename}"

    base_dir = Path(settings.storage_local_root)
    absolute = base_dir / storage_key
    absolute.parent.mkdir(parents=True, exist_ok=True)
    absolute.write_bytes(body)

    signed_url = f"{settings.public_app_url}/static/{storage_key}"

    return ProofUploadResponse(
        proof_path=storage_key,
        proof_url=signed_url,
    )