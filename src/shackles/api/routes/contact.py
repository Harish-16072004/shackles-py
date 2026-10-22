"""Contact form submission."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.api.deps import OptionalUser
from shackles.db.session import get_session
from shackles.models.contact_message import ContactMessage
from shackles.repositories.contact_message_repo import (
    ContactMessageRepository,
)
from shackles.schemas.common import MessageResponse
from shackles.schemas.contact_message import ContactMessageCreate


router = APIRouter(tags=["contact"])


@router.post("/contact", response_model=MessageResponse, status_code=201)
async def submit_contact_form(
    payload: ContactMessageCreate,
    user: OptionalUser,
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Submit a contact form. Works for logged-in and anonymous users."""
    repo = ContactMessageRepository(session)
    msg = ContactMessage(
        name=payload.name,
        email=payload.email,
        mobile=payload.mobile,
        message=payload.message,
        user_id=user.id if user else None,
    )
    session.add(msg)
    await session.flush()
    await session.commit()
    return MessageResponse(message="Your message has been received.")