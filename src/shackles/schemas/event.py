"""Event schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import Field, model_validator

from shackles.models.enums import EventCategory, EventParticipationMode
from shackles.schemas.common import ApiBase, ApiRead, ApiWrite


class EventBase(ApiBase):
    """Shared event fields."""

    name: str = Field(min_length=1, max_length=200)
    year: int = Field(ge=2000, le=3000)
    type: str | None = Field(default=None, max_length=50)
    category: EventCategory | None = None
    day_label: str | None = Field(default=None, max_length=20)
    date: datetime | None = None
    end_date: datetime | None = None
    is_all_day: bool = False
    description: str | None = Field(default=None, max_length=2000)
    rules_url: str | None = Field(default=None, max_length=500)
    submission_url: str | None = Field(default=None, max_length=500)
    submission_deadline: datetime | None = None
    requires_document_submission: bool = False
    coordinator_name: str | None = Field(default=None, max_length=200)
    coordinator_phone: str | None = Field(default=None, max_length=20)
    trainer_name: str | None = Field(default=None, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_phone: str | None = Field(default=None, max_length=20)
    participation_mode: EventParticipationMode = EventParticipationMode.INDIVIDUAL
    team_min_size: int | None = Field(default=None, ge=1)
    team_max_size: int | None = Field(default=None, ge=1)
    max_teams: int | None = Field(default=None, ge=1)
    max_participants: int | None = Field(default=None, ge=1)
    is_active: bool = True

    @model_validator(mode="after")
    def _validate_team_sizes(self) -> "EventBase":
        if (
            self.team_min_size is not None
            and self.team_max_size is not None
            and self.team_min_size > self.team_max_size
        ):
            raise ValueError("team_min_size cannot exceed team_max_size")
        return self

    @model_validator(mode="after")
    def _validate_dates(self) -> "EventBase":
        if self.date and self.end_date and self.end_date < self.date:
            raise ValueError("end_date cannot be before date")
        return self


class EventCreate(EventBase, ApiWrite):
    """Payload for POST /api/admin/events."""

    pass


class EventUpdate(ApiWrite):
    """Payload for PATCH /api/admin/events/{id} — all fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: str | None = Field(default=None, max_length=50)
    category: EventCategory | None = None
    day_label: str | None = Field(default=None, max_length=20)
    date: datetime | None = None
    end_date: datetime | None = None
    is_all_day: bool | None = None
    description: str | None = Field(default=None, max_length=2000)
    rules_url: str | None = Field(default=None, max_length=500)
    submission_url: str | None = Field(default=None, max_length=500)
    submission_deadline: datetime | None = None
    requires_document_submission: bool | None = None
    coordinator_name: str | None = Field(default=None, max_length=200)
    coordinator_phone: str | None = Field(default=None, max_length=20)
    trainer_name: str | None = Field(default=None, max_length=200)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_phone: str | None = Field(default=None, max_length=20)
    participation_mode: EventParticipationMode | None = None
    team_min_size: int | None = Field(default=None, ge=1)
    team_max_size: int | None = Field(default=None, ge=1)
    max_teams: int | None = Field(default=None, ge=1)
    max_participants: int | None = Field(default=None, ge=1)
    is_active: bool | None = None
    is_archived: bool | None = None


class EventRead(ApiRead):
    """Public event representation."""

    id: UUID
    name: str
    year: int
    type: str | None
    category: EventCategory | None
    day_label: str | None
    date: datetime | None
    end_date: datetime | None
    is_all_day: bool
    description: str | None
    rules_url: str | None
    submission_url: str | None
    submission_deadline: datetime | None
    requires_document_submission: bool
    coordinator_name: str | None
    coordinator_phone: str | None
    trainer_name: str | None
    contact_name: str | None
    contact_phone: str | None
    participation_mode: EventParticipationMode
    team_min_size: int | None
    team_max_size: int | None
    max_teams: int | None
    max_participants: int | None
    is_active: bool
    is_archived: bool
    is_template: bool
    created_at: datetime
    updated_at: datetime


class EventListFilters(ApiWrite):
    """Query parameters for filtering event lists."""

    year: int | None = Field(default=None, ge=2000, le=3000)
    category: EventCategory | None = None
    type: str | None = None
    is_active: bool | None = None
    is_template: bool | None = None
    search: str | None = Field(default=None, max_length=200)