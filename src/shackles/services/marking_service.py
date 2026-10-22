"""MarkingService — criteria setup and judge mark submission."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shackles.errors import (
    CRITERIA_ALREADY_EXISTS,
    CRITERIA_NOT_FOUND,
    INVALID_MARKS,
    DomainError,
)
from shackles.repositories.event_repo import EventRepository
from shackles.repositories.marking_repo import (
    ComponentMarkRepository,
    CriteriaComponentRepository,
    JudgeMarkingRepository,
    MarkingCriteriaRepository,
    TeamMarkRepository,
)
from shackles.repositories.team_repo import TeamRepository
from shackles.repositories.user_repo import UserRepository
from shackles.schemas.marking import (
    CriteriaComponentCreate,
    JudgeMarkingCreate,
    MarkingCriteriaCreate,
)


class MarkingService:
    """Criteria creation and mark submission."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.events = EventRepository(session)
        self.users = UserRepository(session)
        self.teams = TeamRepository(session)
        self.criteria = MarkingCriteriaRepository(session)
        self.components = CriteriaComponentRepository(session)
        self.judge_marks = JudgeMarkingRepository(session)
        self.component_marks = ComponentMarkRepository(session)
        self.team_marks = TeamMarkRepository(session)

    # ========================================================
    # Criteria setup
    # ========================================================

    async def create_criteria(
        self,
        event_id: UUID,
        data: MarkingCriteriaCreate,
    ):
        """Create marking criteria with components for an event.

        Validates that component weights sum to 100.
        """
        event = await self.events.get(event_id)
        if event is None:
            raise DomainError("EVENT_NOT_FOUND", "Event not found.")

        if await self.criteria.event_has_criteria(event_id):
            raise DomainError(
                CRITERIA_ALREADY_EXISTS,
                "Marking criteria already exists for this event.",
            )

        # Weights must sum to 100
        total_weight = sum(c.weight_percentage for c in data.components)
        if total_weight != 100:
            raise DomainError(
                INVALID_MARKS,
                f"Component weights must sum to 100% (currently {total_weight}%).",
            )

        criteria = await self.criteria.create(
            event_id=event_id,
            name=data.name,
            description=data.description,
            max_marks=data.max_marks,
            number_of_judges=data.number_of_judges,
        )

        for order, comp in enumerate(data.components):
            await self.components.create(
                marking_criteria_id=criteria.id,
                name=comp.name,
                description=comp.description,
                weight_percentage=comp.weight_percentage,
                max_marks_for_component=comp.max_marks_for_component,
                order=comp.order if comp.order is not None else order,
            )

        return await self.criteria.get_by_event_id_with_components(event_id)

    async def get_criteria_for_event(self, event_id: UUID):
        """Fetch criteria + components. Raises if not set up."""
        return await self.criteria.get_by_event_id_or_raise(event_id)

    # ========================================================
    # Judge mark submission
    # ========================================================

    async def submit_judge_marks(
        self,
        event_id: UUID,
        judge_id: UUID,
        marks: list[JudgeMarkingCreate],
    ) -> dict:
        """Submit one judge's marks for multiple (team, component) pairs.

        For each mark:
          1. Validate the component belongs to the event
          2. Validate marks_awarded ≤ component's max
          3. Upsert the JudgeMarking row

        Then, for each affected team, recalculate the aggregate TeamMark.

        Returns:
            {
              "teams_updated": N,
              "marks_recorded": M,
              "recalculated": [team_id, ...],
            }
        """
        criteria = await self.criteria.get_by_event_id_with_components(event_id)
        if criteria is None:
            raise DomainError(
                CRITERIA_NOT_FOUND,
                "Marking criteria not set up for this event.",
            )

        components_by_id = {c.id: c for c in criteria.components}

        # Validate + upsert
        teams_affected: set[UUID] = set()
        for mark in marks:
            component = components_by_id.get(mark.component_id)
            if component is None:
                raise DomainError(
                    INVALID_MARKS,
                    f"Component {mark.component_id} not found in criteria.",
                )
            if mark.marks_awarded > component.max_marks_for_component:
                raise DomainError(
                    INVALID_MARKS,
                    f"Marks for '{component.name}' exceed max "
                    f"({component.max_marks_for_component}).",
                )

            await self.judge_marks.upsert(
                team_id=mark.team_id,
                marking_criteria_id=criteria.id,
                component_id=component.id,
                judge_id=judge_id,
                marks_awarded=Decimal(mark.marks_awarded),
                judge_notes=mark.judge_notes,
            )
            teams_affected.add(mark.team_id)

        # Recalculate for each affected team
        for team_id in teams_affected:
            await self.team_marks.recalculate_from_judge_marks(
                team_id, criteria.id
            )

        return {
            "teams_updated": len(teams_affected),
            "marks_recorded": len(marks),
            "recalculated": [str(t) for t in teams_affected],
        }

    # ========================================================
    # Leaderboard
    # ========================================================

    async def get_leaderboard(self, event_id: UUID) -> dict:
        """Compute the leaderboard for an event.

        Returns a dict ready for the LeaderboardResponse schema.
        """
        criteria = await self.criteria.get_by_event_id_with_components(event_id)
        if criteria is None:
            return {
                "event_id": str(event_id),
                "criteria_name": "Not configured",
                "max_marks": 0,
                "number_of_judges": 0,
                "teams": [],
                "total_teams_submitted": 0,
            }

        team_marks = await self.team_marks.list_submitted_with_details(criteria.id)

        entries: list[dict] = []
        for idx, tm in enumerate(team_marks):
            team = tm.team
            entries.append({
                "rank": idx + 1,
                "team_id": str(team.id),
                "team_name": team.name,
                "member_count": team.member_count,
                "total_marks": float(tm.total_marks),
                "component_marks": [
                    {
                        "component_id": str(cm.component_id),
                        "component_name": cm.component.name,
                        "average_marks": float(cm.average_marks),
                        "judge_count": cm.judge_count,
                    }
                    for cm in tm.component_marks
                ],
            })

        return {
            "event_id": str(event_id),
            "criteria_name": criteria.name,
            "max_marks": criteria.max_marks,
            "number_of_judges": criteria.number_of_judges,
            "teams": entries,
            "total_teams_submitted": len(entries),
        }

    async def get_team_marks(
        self,
        team_id: UUID,
        event_id: UUID,
    ) -> dict | None:
        """Fetch one team's aggregate marks."""
        criteria = await self.criteria.get_by_event_id(event_id)
        if criteria is None:
            return None
        tm = await self.team_marks.get_with_component_marks(team_id, criteria.id)
        if tm is None:
            return None
        return {
            "team_id": str(team_id),
            "marking_criteria_id": str(criteria.id),
            "total_marks": float(tm.total_marks),
            "judge_count": tm.judge_count,
            "is_submitted": tm.is_submitted,
            "submitted_at": tm.submitted_at.isoformat() if tm.submitted_at else None,
            "component_marks": [
                {
                    "component_id": str(cm.component_id),
                    "average_marks": float(cm.average_marks),
                    "judge_count": cm.judge_count,
                }
                for cm in tm.component_marks
            ],
        }