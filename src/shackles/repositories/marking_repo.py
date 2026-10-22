"""Marking repositories — criteria, components, and aggregate marks.

This module contains five tightly-coupled repository classes:

  - MarkingCriteriaRepository   — the top-level criteria per event
  - CriteriaComponentRepository — the weighted components within criteria
  - TeamMarkRepository          — the aggregate score for one team
  - ComponentMarkRepository     — the aggregate score per component
  - JudgeMarkingRepository      — raw marks from individual judges

The aggregation logic (recalculate_from_judge_marks) lives on
TeamMarkRepository because it touches all three of the mark tables.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from shackles.errors import (
    CRITERIA_ALREADY_EXISTS,
    CRITERIA_NOT_FOUND,
    DomainError,
)
from shackles.models.component_mark import ComponentMark
from shackles.models.criteria_component import CriteriaComponent
from shackles.models.judge_marking import JudgeMarking
from shackles.models.marking_criteria import MarkingCriteria
from shackles.models.team_mark import TeamMark
from shackles.repositories.base import BaseRepository


# ============================================================
# MarkingCriteriaRepository
# ============================================================

class MarkingCriteriaRepository(BaseRepository[MarkingCriteria]):
    """Data access for MarkingCriteria (one per event)."""

    model = MarkingCriteria

    async def get_by_event_id(self, event_id: UUID) -> MarkingCriteria | None:
        """Fetch the criteria for an event (unique per event)."""
        stmt = select(MarkingCriteria).where(
            MarkingCriteria.event_id == event_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_event_id_with_components(
        self, event_id: UUID
    ) -> MarkingCriteria | None:
        """Fetch criteria with components eagerly loaded."""
        stmt = (
            select(MarkingCriteria)
            .where(MarkingCriteria.event_id == event_id)
            .options(selectinload(MarkingCriteria.components))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_event_id_or_raise(
        self, event_id: UUID
    ) -> MarkingCriteria:
        """Fetch criteria by event. Raises if not found."""
        criteria = await self.get_by_event_id(event_id)
        if criteria is None:
            raise DomainError(
                CRITERIA_NOT_FOUND,
                "No marking criteria configured for this event.",
                {"event_id": str(event_id)},
            )
        return criteria

    async def event_has_criteria(self, event_id: UUID) -> bool:
        """Check whether an event already has criteria configured."""
        stmt = (
            select(func.count())
            .select_from(MarkingCriteria)
            .where(MarkingCriteria.event_id == event_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def ensure_no_criteria(self, event_id: UUID) -> None:
        """Raise CRITERIA_ALREADY_EXISTS if the event already has criteria."""
        if await self.event_has_criteria(event_id):
            raise DomainError(
                CRITERIA_ALREADY_EXISTS,
                "Marking criteria already exists for this event.",
                {"event_id": str(event_id)},
            )


# ============================================================
# CriteriaComponentRepository
# ============================================================

class CriteriaComponentRepository(BaseRepository[CriteriaComponent]):
    """Data access for CriteriaComponent."""

    model = CriteriaComponent

    async def list_for_criteria(
        self, marking_criteria_id: UUID
    ) -> list[CriteriaComponent]:
        """List all components for a criteria, ordered by `order`."""
        stmt = (
            select(CriteriaComponent)
            .where(
                CriteriaComponent.marking_criteria_id == marking_criteria_id
            )
            .order_by(CriteriaComponent.order.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_criteria_and_order(
        self,
        marking_criteria_id: UUID,
        order: int,
    ) -> CriteriaComponent | None:
        """Fetch a component by (criteria, order) — unique."""
        stmt = select(CriteriaComponent).where(
            CriteriaComponent.marking_criteria_id == marking_criteria_id,
            CriteriaComponent.order == order,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def next_order(self, marking_criteria_id: UUID) -> int:
        """Compute the next `order` value for a new component."""
        stmt = select(func.max(CriteriaComponent.order)).where(
            CriteriaComponent.marking_criteria_id == marking_criteria_id
        )
        result = await self.session.execute(stmt)
        max_order = result.scalar_one_or_none()
        return (max_order or -1) + 1

    async def total_weight(self, marking_criteria_id: UUID) -> Decimal:
        """Sum of weight_percentage for all components in a criteria."""
        stmt = (
            select(
                func.coalesce(
                    func.sum(CriteriaComponent.weight_percentage), 0
                )
            )
            .where(
                CriteriaComponent.marking_criteria_id == marking_criteria_id
            )
        )
        result = await self.session.execute(stmt)
        value = result.scalar_one()
        return Decimal(str(value))


# ============================================================
# JudgeMarkingRepository
# ============================================================

class JudgeMarkingRepository(BaseRepository[JudgeMarking]):
    """Data access for raw judge marks."""

    model = JudgeMarking

    async def list_for_team_and_component(
        self,
        team_id: UUID,
        component_id: UUID,
    ) -> list[JudgeMarking]:
        """List all judges' marks for one (team, component).

        Used by the aggregate recalculation to compute the average.
        """
        stmt = select(JudgeMarking).where(
            JudgeMarking.team_id == team_id,
            JudgeMarking.component_id == component_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_unique_key(
        self,
        team_id: UUID,
        marking_criteria_id: UUID,
        component_id: UUID,
        judge_id: UUID,
    ) -> JudgeMarking | None:
        """Fetch the single judge mark matching the unique constraint."""
        stmt = select(JudgeMarking).where(
            JudgeMarking.team_id == team_id,
            JudgeMarking.marking_criteria_id == marking_criteria_id,
            JudgeMarking.component_id == component_id,
            JudgeMarking.judge_id == judge_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        team_id: UUID,
        marking_criteria_id: UUID,
        component_id: UUID,
        judge_id: UUID,
        marks_awarded: Decimal,
        judge_notes: str | None = None,
    ) -> JudgeMarking:
        """Insert or update a judge's mark for one component of one team."""
        existing = await self.get_by_unique_key(
            team_id, marking_criteria_id, component_id, judge_id
        )
        if existing is not None:
            existing.marks_awarded = marks_awarded
            if judge_notes is not None:
                existing.judge_notes = judge_notes
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        obj = JudgeMarking(
            team_id=team_id,
            marking_criteria_id=marking_criteria_id,
            component_id=component_id,
            judge_id=judge_id,
            marks_awarded=marks_awarded,
            judge_notes=judge_notes,
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def count_for_component(
        self,
        team_id: UUID,
        component_id: UUID,
    ) -> int:
        """Count how many judges have submitted marks for a component."""
        stmt = (
            select(func.count())
            .select_from(JudgeMarking)
            .where(
                JudgeMarking.team_id == team_id,
                JudgeMarking.component_id == component_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_for_team(
        self,
        team_id: UUID,
    ) -> list[JudgeMarking]:
        """List all judge marks for a team across all components/judges."""
        stmt = (
            select(JudgeMarking)
            .where(JudgeMarking.team_id == team_id)
            .order_by(
                JudgeMarking.component_id.asc(),
                JudgeMarking.judge_id.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


# ============================================================
# ComponentMarkRepository
# ============================================================

class ComponentMarkRepository(BaseRepository[ComponentMark]):
    """Data access for per-component aggregate marks."""

    model = ComponentMark

    async def get_by_team_mark_and_component(
        self,
        team_mark_id: UUID,
        component_id: UUID,
    ) -> ComponentMark | None:
        """Fetch the aggregate for one (team_mark, component)."""
        stmt = select(ComponentMark).where(
            ComponentMark.team_mark_id == team_mark_id,
            ComponentMark.component_id == component_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        team_mark_id: UUID,
        component_id: UUID,
        average_marks: Decimal,
        judge_count: int,
    ) -> ComponentMark:
        """Insert or update the aggregate for one (team_mark, component)."""
        existing = await self.get_by_team_mark_and_component(
            team_mark_id, component_id
        )
        if existing is not None:
            existing.average_marks = average_marks
            existing.judge_count = judge_count
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        obj = ComponentMark(
            team_mark_id=team_mark_id,
            component_id=component_id,
            average_marks=average_marks,
            judge_count=judge_count,
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def list_for_team_mark(
        self, team_mark_id: UUID
    ) -> list[ComponentMark]:
        """List all component aggregates for a team mark."""
        stmt = (
            select(ComponentMark)
            .where(ComponentMark.team_mark_id == team_mark_id)
            .order_by(ComponentMark.component_id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_for_component(
        self,
        team_mark_id: UUID,
        component_id: UUID,
    ) -> int:
        """Delete the aggregate for one component. Returns rows deleted."""
        stmt = delete(ComponentMark).where(
            ComponentMark.team_mark_id == team_mark_id,
            ComponentMark.component_id == component_id,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0


# ============================================================
# TeamMarkRepository — including the aggregate recalculation
# ============================================================

class TeamMarkRepository(BaseRepository[TeamMark]):
    """Data access for team aggregate marks.

    Also owns the multi-table recalculation logic:
      1. For each component: average judge marks -> ComponentMark
      2. Weighted sum -> TeamMark.total_marks
    """

    model = TeamMark

    # ---------------- Lookups ----------------

    async def get_by_team_and_criteria(
        self,
        team_id: UUID,
        marking_criteria_id: UUID,
    ) -> TeamMark | None:
        """Fetch the team mark for one (team, criteria)."""
        stmt = select(TeamMark).where(
            TeamMark.team_id == team_id,
            TeamMark.marking_criteria_id == marking_criteria_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        team_id: UUID,
        marking_criteria_id: UUID,
    ) -> TeamMark:
        """Fetch the team mark or create an empty one."""
        existing = await self.get_by_team_and_criteria(
            team_id, marking_criteria_id
        )
        if existing is not None:
            return existing

        obj = TeamMark(
            team_id=team_id,
            marking_criteria_id=marking_criteria_id,
            total_marks=Decimal("0"),
            judge_count=0,
            is_submitted=False,
        )
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_with_component_marks(
        self,
        team_id: UUID,
        marking_criteria_id: UUID,
    ) -> TeamMark | None:
        """Fetch a team mark with its component marks eagerly loaded."""
        stmt = (
            select(TeamMark)
            .where(
                TeamMark.team_id == team_id,
                TeamMark.marking_criteria_id == marking_criteria_id,
            )
            .options(selectinload(TeamMark.component_marks))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ---------------- Lists ----------------

    async def list_for_criteria(
        self,
        marking_criteria_id: UUID,
        *,
        only_submitted: bool = True,
    ) -> list[TeamMark]:
        """List team marks for a criteria, optionally only submitted ones.

        Ordered by total_marks descending (highest score first).
        """
        stmt = select(TeamMark).where(
            TeamMark.marking_criteria_id == marking_criteria_id
        )
        if only_submitted:
            stmt = stmt.where(TeamMark.is_submitted.is_(True))
        stmt = stmt.order_by(
            TeamMark.total_marks.desc(),
            TeamMark.created_at.desc(),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_submitted_with_details(
        self,
        marking_criteria_id: UUID,
    ) -> list[TeamMark]:
        """List submitted team marks with team + component marks loaded.

        This is the leaderboard query — eager-loads everything needed to
        render the leaderboard without N+1 queries.
        """
        stmt = (
            select(TeamMark)
            .where(
                TeamMark.marking_criteria_id == marking_criteria_id,
                TeamMark.is_submitted.is_(True),
            )
            .options(
                selectinload(TeamMark.team),
                selectinload(TeamMark.component_marks).selectinload(
                    ComponentMark.component
                ),
            )
            .order_by(
                TeamMark.total_marks.desc(),
                TeamMark.created_at.desc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ---------------- Counts ----------------

    async def count_submitted(
        self, marking_criteria_id: UUID
    ) -> int:
        """Count submitted team marks for a criteria."""
        stmt = (
            select(func.count())
            .select_from(TeamMark)
            .where(
                TeamMark.marking_criteria_id == marking_criteria_id,
                TeamMark.is_submitted.is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ---------------- Recalculation ----------------

    async def recalculate_from_judge_marks(
        self,
        team_id: UUID,
        marking_criteria_id: UUID,
    ) -> TeamMark:
        """Recompute the team's total from all judge marks.

        Steps:
          1. Load criteria + components
          2. Get or create the team's TeamMark
          3. For each component:
             - Load all JudgeMarking rows
             - If any: compute average, upsert ComponentMark
             - If none: delete any stale ComponentMark for that component
          4. Compute the weighted total per the criteria formula
          5. Store total_marks + judge_count on TeamMark
        """
        # ---- 1. Load criteria with components ----
        criteria_stmt = (
            select(MarkingCriteria)
            .where(MarkingCriteria.id == marking_criteria_id)
            .options(selectinload(MarkingCriteria.components))
        )
        criteria = (
            await self.session.execute(criteria_stmt)
        ).scalar_one_or_none()

        if criteria is None:
            raise DomainError(
                CRITERIA_NOT_FOUND,
                f"Marking criteria {marking_criteria_id} not found.",
                {"marking_criteria_id": str(marking_criteria_id)},
            )

        # ---- 2. Get or create the TeamMark ----
        team_mark = await self.get_or_create(team_id, marking_criteria_id)

        # ---- 3. Recalc each component ----
        total_raw = Decimal("0")
        distinct_judges: set[UUID] = set()

        component_mark_repo = ComponentMarkRepository(self.session)
        judge_repo = JudgeMarkingRepository(self.session)

        for component in criteria.components:
            judge_marks = await judge_repo.list_for_team_and_component(
                team_id, component.id
            )

            if not judge_marks:
                # No marks for this component — clear stale aggregate
                await component_mark_repo.delete_for_component(
                    team_mark.id, component.id
                )
                continue

            # Compute average of judges' marks
            marks_sum = sum(
                (m.marks_awarded for m in judge_marks), Decimal("0")
            )
            avg = marks_sum / Decimal(len(judge_marks))

            # Quantize to 2 decimal places (matches DB column)
            avg = avg.quantize(Decimal("0.01"))

            # Weighted contribution
            max_for_component = Decimal(component.max_marks_for_component)
            weighted = (avg / max_for_component) * component.weight_percentage
            total_raw += weighted

            # Upsert the per-component aggregate
            await component_mark_repo.upsert(
                team_mark_id=team_mark.id,
                component_id=component.id,
                average_marks=avg,
                judge_count=len(judge_marks),
            )

            # Track distinct judges
            for m in judge_marks:
                distinct_judges.add(m.judge_id)

        # ---- 4. Scale to criteria.max_marks ----
        final_total = (total_raw / Decimal("100")) * Decimal(criteria.max_marks)
        final_total = final_total.quantize(Decimal("0.01"))

        # ---- 5. Persist on TeamMark ----
        now = datetime.now(timezone.utc)
        team_mark.total_marks = final_total
        team_mark.judge_count = (
            len(distinct_judges)
            if distinct_judges
            else criteria.number_of_judges
        )
        team_mark.is_submitted = True
        team_mark.submitted_at = now

        await self.session.flush()
        await self.session.refresh(team_mark)
        return team_mark

    async def mark_unsubmitted(
        self, team_id: UUID, marking_criteria_id: UUID
    ) -> bool:
        """Mark a team's score as not yet submitted (revert)."""
        tm = await self.get_by_team_and_criteria(team_id, marking_criteria_id)
        if tm is None:
            return False
        tm.is_submitted = False
        tm.submitted_at = None
        await self.session.flush()
        return True