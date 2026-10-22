"""QR token generation, payload encoding, and image rendering."""

import base64
import json
import secrets
from io import BytesIO
from typing import Any
from uuid import UUID

import qrcode
from qrcode.constants import ERROR_CORRECT_H


# ============================================================
# Token generation
# ============================================================

def generate_qr_token() -> str:
    """Generate a cryptographically random QR token.

    Returns 64 hex characters (32 random bytes). This is what gets
    stored as `User.qr_token` — the token is what scanners look up.
    """
    return secrets.token_hex(32)


# ============================================================
# Payload encoding / decoding
# ============================================================

def encode_qr_payload(
    qr_token: str,
    shackles_id: str | None,
    year: int,
) -> str:
    """Encode a USER payload for embedding in the QR image.

    Args:
        qr_token: The user's `qr_token` field (NOT the user UUID). This
            is the lookup key the scanner uses to find the user.
        shackles_id: The user's Shackles ID (e.g., 'SH26G001').
        year: The symposium year.

    Returns:
        A URL-safe base64 string. Decoding gives:

            {
              "v": 1,
              "type": "USER",
              "uid": "<qr_token>",
              "sid": "SH26G001",
              "y": 2026
            }
    """
    payload = {
        "v": 1,
        "type": "USER",
        "uid": qr_token,
        "sid": shackles_id,
        "y": year,
    }
    raw = json.dumps(payload, separators=(",", ":"))
    encoded = base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def decode_qr_payload(data: str) -> dict[str, Any]:
    """Decode a QR payload string back into a dict.

    Raises:
        ValueError: if the payload is malformed, has an unsupported
            version, or is missing required fields.
    """
    if not data or not isinstance(data, str):
        raise ValueError("QR payload is empty.")

    # Restore base64 padding
    stripped = data.strip()
    padding = (4 - len(stripped) % 4) % 4
    padded = stripped + ("=" * padding)

    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid QR code.") from exc

    if not isinstance(payload, dict):
        raise ValueError("Invalid QR payload structure.")

    version = payload.get("v")
    if version != 1:
        raise ValueError(f"Unsupported QR version: {version}")

    qr_type = payload.get("type")
    if qr_type not in ("USER", "TEAM"):
        raise ValueError(f"Unknown QR type: {qr_type}")

    if qr_type == "USER":
        if not payload.get("uid"):
            raise ValueError("USER QR missing 'uid'.")
    elif qr_type == "TEAM":
        if not payload.get("tid") or not payload.get("eid"):
            raise ValueError("TEAM QR missing 'tid' or 'eid'.")

    if not isinstance(payload.get("y"), int):
        raise ValueError("QR payload missing valid year.")

    return payload


# ============================================================
# Image generation
# ============================================================

def generate_qr_image(
    payload: str,
    *,
    box_size: int = 10,
    border: int = 2,
) -> bytes:
    """Render a QR payload to a PNG image.

    Args:
        payload: The encoded payload string.
        box_size: Pixel size of each QR module.
        border: Number of modules of white space around the QR.

    Returns:
        PNG image bytes ready for upload to storage.
    """
    qr = qrcode.QRCode(
        version=None,               # auto-size
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()