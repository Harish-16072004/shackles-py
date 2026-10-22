"""Marking schemas — criteria, components, marks."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from shackles.schemas.common import ApiBase, ApiRead, ApiWrite


# ============================================================
# CriteriaComponent
# ============================================================

class CriteriaComponentBase(ApiBase):
    """Shared component fields."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    weight_percentage: Decimal = Field(ge=0, le=100, decimal_places=2)
    max_marks_for_component: int = Field(ge=1, le=10000)
    order: int = Field(default=0, ge=0)


class CriteriaComponentCreate(CriteriaComponentBase, ApiWrite):
    """Payload for creating a component."""

    pass


class CriteriaComponentRead(CriteriaComponentBase, ApiRead):
    """Public component representation."""

    id: UUID
    marking_criteria_id: UUID
    created_at: datetime
    updated_at: datetime


# ============================================================
# MarkingCriteria
# ============================================================

class MarkingCriteriaBase(ApiBase):
    """Shared criteria fields."""

    name: str = Field(default="Default Marking Criteria", max_length=255)
    description: str | None = Field(default=None, max_length=500)
    max_marks: int = Field(default=100, ge=1, le=10000)
    number_of_judges: int = Field(default=3, ge=1, le=100)


class MarkingCriteriaCreate(MarkingCriteriaBase, ApiWrite):
    """Payload for POST /api/admin/events/{id}/criteria."""

    components: list[CriteriaComponentCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_weights_sum_to_100(self) -> "MarkingCriteriaCreate":
        total_weight = sum(c.weight_percentage for c in self.components)
        if total_weight != 100:
            raise ValueError(
                f"Component weights must sum to 100% (currently {total_weight}%)"
            )
        return self


class MarkingCriteriaRead(MarkingCriteriaBase, ApiRead):
    """Public criteria representation."""

    id: UUID
    event_id: UUID
    components: list[CriteriaComponentRead] = []
    created_at: datetime
    updated_at: datetime


# ============================================================
# ComponentMark
# ============================================================

class ComponentMarkRead(ApiRead):
    """Public component mark representation."""

    id: UUID
    team_mark_id: UUID
    component_id: UUID
    average_marks: Decimal
    judge_count: int


# ============================================================
# TeamMark
# ============================================================

class TeamMarkRead(ApiRead):
    """Public team mark representation."""

    id: UUID
    team_id: UUID
    marking_criteria_id: UUID
    total_marks: Decimal
    judge_count: int
    is_submitted: bool
    submitted_at: datetime | None
    component_marks: list[ComponentMarkRead] = []


class TeamMarkWithTeam(TeamMarkRead):
    """TeamMark with team name and member count for leaderboards."""

    team_name: str
    team_member_count: int
    rank: int | None = None


# ============================================================
# JudgeMarking
# ============================================================

class JudgeMarkingCreate(ApiWrite):
    """Payload for a judge submitting marks for a team."""

    team_id: UUID
    component_id: UUID
    marks_awarded: Decimal = Field(ge=0)
    judge_notes: str | None = Field(default=None, max_length=500)


class JudgeMarkingRead(ApiRead):
    """Public judge marking representation."""

    id: UUID
    team_id: UUID
    marking_criteria_id: UUID
    component_id: UUID
    judge_id: UUID
    marks_awarded: Decimal
    judge_notes: str | None
    created_at: datetime
    updated_at: datetime


# ============================================================
# Bulk submission
# ============================================================

class TeamMarksSubmission(ApiWrite):
    """A team's marks for all components, as entered by one judge."""

    team_id: UUID
    component_marks: list[dict] = Field(min_length=1)


class BulkMarksSubmit(ApiWrite):
    """Payload for POST /api/marking/submit-marks."""

    event_id: UUID
    judge_id: UUID | None = None
    team_marks: list[TeamMarksSubmission] = Field(min_length=1)


# ============================================================
# Leaderboard
# ============================================================

class LeaderboardEntry(ApiRead):
    """A single row in the leaderboard."""

    rank: int
    team_id: UUID
    team_name: str
    member_count: int
    total_marks: Decimal
    component_marks: list[dict] = []


class LeaderboardResponse(ApiRead):
    """Full leaderboard for an event."""

    event_id: UUID
    criteria_name: str
    max_marks: int
    number_of_judges: int
    teams: list[LeaderboardEntry]
    total_teams_submitted: int