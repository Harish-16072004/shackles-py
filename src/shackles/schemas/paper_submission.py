"""PaperSubmission schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field

from shackles.models.enums import PaperSelectionStatus
from shackles.schemas.common import ApiBase, ApiRead, ApiWrite


class PaperSubmissionBase(ApiBase):
    """Shared paper submission fields."""

    abstract_url: str | None = Field(default=None, max_length=500)
    abstract_deadline: datetime | None = None
    selection_note: str | None = Field(default=None, max_length=1000)
    presentation_url: str | None = Field(default=None, max_length=500)
    presentation_deadline: datetime | None = None


class PaperSubmissionRead(PaperSubmissionBase, ApiRead):
    """Public paper submission representation."""

    id: UUID
    team_id: UUID
    event_id: UUID
    abstract_submitted_at: datetime | None
    selection_status: PaperSelectionStatus
    selected_at: datetime | None
    selected_by: str | None
    presentation_submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PaperSelectionUpdate(ApiWrite):
    """Payload for admin updating selection status."""

    status: PaperSelectionStatus
    selection_note: str | None = Field(default=None, max_length=1000)


class DeadlineUpdate(ApiWrite):
    """Payload for admin setting a deadline."""

    deadline: datetime