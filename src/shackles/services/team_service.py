"""TeamService — create, join, lock, invite, and manage teams.

This service covers the full team lifecycle for TEAM-mode events:

  - create_team          — leader creates a team with a join code
  - join_by_code         — member joins using the team's join code
  - join_by_team_code    — member joins using the event-scoped team code
  - join_by_invite_token — member joins using an emailed invite token
  - create_invites       — leader creates token-based email invitations
  - lock_team            — leader/admin finalizes the roster
  - change_leader        — admin swaps the team leader
  - remove_member        — leader/admin removes a member
  - delete_team          — admin deletes the whole team
  - bulk_register        — on-spot kiosk: register a roster in one call

Every method performs eligibility checks (payment, package, time clash,
capacity) via shared helpers. None of them commit — the API layer owns
the transaction boundary.
"""

from datetime import datetime, timedelta, timezone
import secrets
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from shackles.config import settings
from shackles.errors import (
    ALREADY_REGISTERED,
    EVENT_FULL,
    EVENT_INACTIVE,
    EVENT_NOT_FOUND,
    EVENT_WRONG_YEAR,
    INVALID_TOKEN,
    JOIN_CODE_INVALID,
    NO_VERIFIED_PACKAGE,
    NOT_TEAM_EVENT,
    PACKAGE_NOT_ALLOWED,
    PAYMENT_NOT_VERIFIED,
    TEAM_ABOVE_MAX_SIZE,
    TEAM_BELOW_MIN_SIZE,
    TEAM_FULL,
    TEAM_LOCKED,
    TEAM_NAME_EXISTS,
    TEAM_NOT_FOUND,
    TIME_CLASH,
    TOKEN_EXPIRED,
    UNAUTHORIZED,
    USER_NOT_FOUND,
    DomainError,
)
from shackles.models.enums import (
    EventParticipationMode,
    RegistrationSource,
    RegistrationSyncStatus,
    TeamMemberRole,
    TeamStatus,
)
from shackles.models.event import Event
from shackles.models.team import Team
from shackles.models.team_invite import TeamInvite
from shackles.models.user import User
from shackles.repositories.event_registration_repo import (
    EventRegistrationRepository,
)
from shackles.repositories.event_repo import EventRepository
from shackles.repositories.paper_submission_repo import (
    PaperSubmissionRepository,
)
from shackles.repositories.payment_repo import PaymentRepository
from shackles.repositories.team_invite_repo import TeamInviteRepository
from shackles.repositories.team_repo import TeamRepository
from shackles.repositories.user_repo import UserRepository
from shackles.services.notifications import (
    notify_abstract_upload_request,
    notify_member_joined,
    notify_team_created,
    notify_team_locked,
)
from shackles.workers.queue import enqueue_email_job


_JOIN_CODE_TTL_DAYS = 7
_INVITE_TTL_DAYS = 7
_TEAM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I, O, 0, 1
_JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"
_TEAM_NAME_BANNED = {
    "TEST", "ADMIN", "DUMMY", "MODERATOR", "ROOT",
    "FUCK", "SHIT", "BITCH", "CUNT",
}


class TeamService:
    """Team lifecycle for TEAM-mode events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.events = EventRepository(session)
        self.payments = PaymentRepository(session)
        self.registrations = EventRegistrationRepository(session)
        self.teams = TeamRepository(session)
        self.invites = TeamInviteRepository(session)
        self.papers = PaperSubmissionRepository(session)

    # ========================================================
    # Create team (leader)
    # ========================================================

    async def create_team(
        self,
        leader_user_id: UUID,
        event_id: UUID,
        team_name: str,
    ) -> Team:
        """Create a new team and register the leader.

        Raises:
            DomainError on any validation failure.
        """
        event = await self._load_and_validate_team_event(event_id)
        leader = await self._load_and_validate_user(leader_user_id)
        await self._check_package_allows(leader.id, event)
        await self._check_time_clash(leader.id, event)

        if await self.registrations.is_registered(leader.id, event.id):
            raise DomainError(
                ALREADY_REGISTERED,
                "You are already registered for this event.",
            )

        normalized_name = _normalize_team_name(team_name)
        name_error = _validate_team_name(team_name, normalized_name)
        if name_error:
            raise DomainError("INVALID_TEAM_NAME", name_error)

        if await self.teams.team_name_exists(event.id, normalized_name):
            raise DomainError(
                TEAM_NAME_EXISTS,
                "A team with this name already exists for this event.",
            )

        # Capacity: teams
        if event.max_teams is not None:
            current_teams = await self.teams.count_for_event(event.id)
            if current_teams + 1 > event.max_teams:
                raise DomainError(
                    EVENT_FULL,
                    "Maximum number of teams already registered.",
                )

        team_code = await self._generate_unique_team_code(event.id)
        join_code = await self._generate_unique_join_code()
        join_expires = datetime.now(timezone.utc) + timedelta(
            days=_JOIN_CODE_TTL_DAYS
        )

        team = await self.teams.create(
            event_id=event.id,
            name=team_name.strip(),
            name_normalized=normalized_name,
            team_code=team_code,
            join_code=join_code,
            join_code_expires_at=join_expires,
            status=TeamStatus.OPEN.value,
            leader_user_id=leader.id,
            leader_contact_phone_snapshot=leader.phone,
            leader_contact_email_snapshot=leader.email,
            member_count=1,
        )

        await self.registrations.create(
            user_id=leader.id,
            event_id=event.id,
            team_id=team.id,
            member_role=TeamMemberRole.LEADER.value,
            team_name=team.name,
            team_size=1,
            source=RegistrationSource.ONLINE.value,
            sync_status=RegistrationSyncStatus.APPLIED.value,
            year=settings.active_year,
        )

        await notify_team_created(
            leader_email=leader.email,
            leader_name=f"{leader.first_name} {leader.last_name}".strip(),
            team_name=team.name,
            event_name=event.name,
            team_code=team.team_code,
            join_code=join_code,
            join_url=f"{settings.public_app_url}/events/join?code={join_code}",
        )

        return team

    # ========================================================
    # Join team (by join code, team code, or invite token)
    # ========================================================

    async def join_by_join_code(
        self,
        user_id: UUID,
        join_code: str,
    ) -> Team:
        """Join an existing team using its global join code."""
        team = await self.teams.get_by_join_code(join_code)
        if team is None:
            raise DomainError(
                JOIN_CODE_INVALID,
                "Invalid join code.",
            )
        if (
            team.join_code_expires_at is not None
            and datetime.now(timezone.utc) > team.join_code_expires_at
        ):
            raise DomainError(
                TOKEN_EXPIRED,
                "This team join code has expired.",
            )
        return await self._do_join(user_id, team)

    async def join_by_team_code(
        self,
        user_id: UUID,
        event_id: UUID,
        team_code: str,
    ) -> Team:
        """Join an existing team using its event-scoped team code."""
        team = await self.teams.get_by_team_code(event_id, team_code)
        if team is None:
            raise DomainError(
                TEAM_NOT_FOUND,
                "Team not found for this event.",
            )
        return await self._do_join(user_id, team)

    async def join_by_invite_token(
        self,
        user_id: UUID,
        event_id: UUID,
        team_code: str,
        invite_token: str,
    ) -> Team:
        """Join a team using an emailed invitation token."""
        invite = await self.invites.get_by_token(invite_token)
        if invite is None:
            raise DomainError(INVALID_TOKEN, "Invalid team invitation token.")
        if invite.used_at is not None:
            raise DomainError(INVALID_TOKEN, "This invitation has already been used.")
        if datetime.now(timezone.utc) > invite.expires_at:
            raise DomainError(TOKEN_EXPIRED, "This invitation has expired.")

        team = await self.teams.get(invite.team_id)
        if team is None or team.event_id != event_id or team.team_code != team_code:
            raise DomainError(
                TEAM_NOT_FOUND,
                "Invitation does not match the specified event and team code.",
            )

        user = await self.users.get(user_id)
        if user is None:
            raise DomainError(USER_NOT_FOUND, "User not found.")
        if (
            invite.invited_email
            and invite.invited_email.lower() != user.email.lower()
        ):
            raise DomainError(
                UNAUTHORIZED,
                "This invitation was sent to a different email address.",
            )

        updated_team = await self._do_join(user_id, team)
        invite.used_at = datetime.now(timezone.utc)
        invite.used_by_user_id = user_id
        await self.session.flush()
        return updated_team

    # ========================================================
    # Team Invites
    # ========================================================

    async def create_invites(
        self,
        team_id: UUID,
        requesting_user_id: UUID,
        emails: list[str],
    ) -> list[TeamInvite]:
        """Create token-based invitations for teammates."""
        team = await self.teams.get(team_id)
        if team is None:
            raise DomainError(TEAM_NOT_FOUND, "Team not found.")
        if team.leader_user_id != requesting_user_id:
            raise DomainError(
                UNAUTHORIZED,
                "Only the team leader can send invitations.",
            )
        if team.status != TeamStatus.OPEN.value:
            raise DomainError(
                TEAM_LOCKED,
                "Cannot send invitations for a locked team.",
            )

        event = await self.events.get(team.event_id)
        event_name = event.name if event else "Event"
        created_invites: list[TeamInvite] = []
        expires_at = datetime.now(timezone.utc) + timedelta(days=_INVITE_TTL_DAYS)

        for raw_email in emails:
            email_clean = raw_email.strip().lower()
            if await self.invites.has_active_invite_for_email(team.id, email_clean):
                continue
            token = secrets.token_urlsafe(24)
            invite = await self.invites.create(
                team_id=team.id,
                invited_email=email_clean,
                invited_by_user_id=requesting_user_id,
                token=token,
                expires_at=expires_at,
            )
            created_invites.append(invite)
            invite_url = (
                f"{settings.public_app_url}/events/{team.event_id}/join"
                f"?team_code={team.team_code}&token={token}"
            )
            await enqueue_email_job(
                template_name="generic",
                to=email_clean,
                context={
                    "subject": f"Team Invitation: {team.name} ({event_name})",
                    "message": (
                        f"You have been invited to join team '{team.name}' for "
                        f"{event_name}. Team Code: {team.team_code}. "
                        f"Accept your invitation at: {invite_url}"
                    ),
                    "year": settings.active_year,
                },
            )

        return created_invites

    async def list_invites_for_team(
        self,
        team_id: UUID,
        requesting_user_id: UUID,
    ) -> list[TeamInvite]:
        """List active invitations for a team (leader or admin only)."""
        team = await self.teams.get(team_id)
        if team is None:
            raise DomainError(TEAM_NOT_FOUND, "Team not found.")
        if team.leader_user_id != requesting_user_id:
            requestor = await self.users.get(requesting_user_id)
            if requestor is None or requestor.role not in ("ADMIN", "COORDINATOR"):
                raise DomainError(
                    UNAUTHORIZED,
                    "Only the team leader or staff can view invitations.",
                )
        return await self.invites.list_active_for_team(team_id)

    async def _do_join(
        self,
        user_id: UUID,
        team: Team,
    ) -> Team:
        """Shared logic for joining a team via code or invite."""
        if team.status != TeamStatus.OPEN.value:
            raise DomainError(
                TEAM_LOCKED,
                "Team registration is already closed.",
            )

        event = await self.events.get(team.event_id)
        if event is None:
            raise DomainError(EVENT_NOT_FOUND, "Event not found.")

        user = await self._load_and_validate_user(user_id)
        await self._check_package_allows(user.id, event)
        await self._check_time_clash(user.id, event)

        if await self.registrations.is_registered(user.id, event.id):
            raise DomainError(
                ALREADY_REGISTERED,
                "You are already registered for this event.",
            )

        max_size = event.team_max_size or 4
        if team.member_count >= max_size:
            raise DomainError(
                TEAM_FULL,
                "Team is already full.",
            )

        await self.registrations.create(
            user_id=user.id,
            event_id=event.id,
            team_id=team.id,
            member_role=TeamMemberRole.MEMBER.value,
            team_name=team.name,
            team_size=1,
            source=RegistrationSource.ONLINE.value,
            sync_status=RegistrationSyncStatus.APPLIED.value,
            year=settings.active_year,
        )
        await self.teams.increment_member_count(team.id)

        # Auto-lock when the team reaches capacity
        refreshed = await self.teams.get(team.id)
        if refreshed is not None and refreshed.member_count >= max_size:
            await self._try_lock_internal(refreshed, locked_by=str(user.id))

        leader = None
        if team.leader_user_id:
            leader = await self.users.get(team.leader_user_id)
        await notify_member_joined(
            member_email=user.email,
            member_name=f"{user.first_name} {user.last_name}".strip(),
            team_name=team.name,
            event_name=event.name,
            leader_name=(
                f"{leader.first_name} {leader.last_name}".strip()
                if leader
                else "Team leader"
            ),
        )

        return refreshed or team

    # ========================================================
    # Lock team
    # ========================================================

    async def lock_team(
        self,
        team_id: UUID,
        *,
        requesting_user_id: UUID,
    ) -> Team:
        """Lock a team, validating min/max sizes.

        Authorization: only the leader or an ADMIN/COORDINATOR can lock.
        """
        team = await self.teams.get_with_members(team_id)
        if team is None:
            raise DomainError(
                TEAM_NOT_FOUND, "Team not found.", {"team_id": str(team_id)}
            )

        # Authorization
        if team.leader_user_id != requesting_user_id:
            requestor = await self.users.get(requesting_user_id)
            if requestor is None or requestor.role not in ("ADMIN", "COORDINATOR"):
                raise DomainError(
                    UNAUTHORIZED,
                    "Only the leader or an admin can lock this team.",
                )

        if team.status == TeamStatus.LOCKED.value:
            raise DomainError(TEAM_LOCKED, "Team is already locked.")

        event = await self.events.get(team.event_id)
        if event is None:
            raise DomainError(EVENT_NOT_FOUND, "Event not found.")

        min_size = event.team_min_size or 2
        max_size = event.team_max_size or 4
        member_count = len(team.members)

        if member_count < min_size:
            raise DomainError(
                TEAM_BELOW_MIN_SIZE,
                f"At least {min_size} members are required to lock the team.",
                {"current": member_count, "min": min_size},
            )
        if member_count > max_size:
            raise DomainError(
                TEAM_ABOVE_MAX_SIZE,
                f"Team exceeds the maximum size of {max_size}.",
                {"current": member_count, "max": max_size},
            )

        # Update team_size on all member registrations
        for reg in team.members:
            reg.team_size = member_count
        await self.session.flush()

        # Optimistic lock
        locked = await self.teams.try_lock(team_id, locked_by=str(requesting_user_id))
        if not locked:
            raise DomainError(
                TEAM_LOCKED,
                "Team was locked by another process.",
            )

        # Create PaperSubmission for document-submission events
        if event.requires_document_submission:
            await self.papers.get_or_create_for_team(
                team_id=team.id,
                event_id=event.id,
                abstract_deadline=event.submission_deadline,
            )

        # Notify members
        for reg in team.members:
            member = await self.users.get(reg.user_id)
            if member is None:
                continue
            await notify_team_locked(
                member_email=member.email,
                member_name=f"{member.first_name} {member.last_name}".strip(),
                team_name=team.name,
                event_name=event.name,
                team_code=team.team_code,
            )
            if event.requires_document_submission:
                await notify_abstract_upload_request(
                    member_email=member.email,
                    member_name=f"{member.first_name} {member.last_name}".strip(),
                    team_name=team.name,
                    event_name=event.name,
                    team_id=str(team.id),
                    abstract_deadline=(
                        event.submission_deadline.isoformat()
                        if event.submission_deadline
                        else None
                    ),
                    is_leader=reg.member_role == TeamMemberRole.LEADER.value,
                )

        refreshed = await self.teams.get(team_id)
        if refreshed is None:
            raise DomainError(TEAM_NOT_FOUND, "Team not found after lock.")
        return refreshed

    async def _try_lock_internal(
        self,
        team: Team,
        *,
        locked_by: str,
    ) -> bool:
        """Internal lock: called after auto-capacity is reached."""
        if team.status != TeamStatus.OPEN.value:
            return False
        return await self.teams.try_lock(team.id, locked_by=locked_by)

    # ========================================================
    # Admin & Leader actions
    # ========================================================

    async def change_leader(
        self,
        team_id: UUID,
        new_leader_user_id: UUID,
    ) -> Team:
        """Swap a team's leader. The old leader becomes a MEMBER."""
        team = await self.teams.get_with_members(team_id)
        if team is None:
            raise DomainError(TEAM_NOT_FOUND, "Team not found.")

        member_user_ids = {reg.user_id for reg in team.members}
        if new_leader_user_id not in member_user_ids:
            raise DomainError(
                "NOT_A_MEMBER",
                "Selected user is not a member of this team.",
            )

        if team.leader_user_id == new_leader_user_id:
            raise DomainError(
                "INVALID_INPUT",
                "This user is already the team leader.",
            )

        old_leader_id = team.leader_user_id
        new_leader = await self.users.get(new_leader_user_id)
        if new_leader is None:
            raise DomainError(USER_NOT_FOUND, "New leader not found.")

        # Update registrations
        for reg in team.members:
            if old_leader_id and reg.user_id == old_leader_id:
                reg.member_role = TeamMemberRole.MEMBER.value
            if reg.user_id == new_leader_user_id:
                reg.member_role = TeamMemberRole.LEADER.value

        # Update team
        team.leader_user_id = new_leader.id
        team.leader_contact_phone_snapshot = new_leader.phone
        team.leader_contact_email_snapshot = new_leader.email

        await self.session.flush()
        await self.session.refresh(team)
        return team

    async def remove_member(
        self,
        team_id: UUID,
        user_id: UUID,
        *,
        requesting_user_id: UUID | None = None,
    ) -> Team | None:
        """Remove a member from a team. Returns the team (or None if
        the team became empty and was deleted)."""
        team = await self.teams.get_with_members(team_id)
        if team is None:
            raise DomainError(TEAM_NOT_FOUND, "Team not found.")

        if requesting_user_id is not None:
            requestor = await self.users.get(requesting_user_id)
            is_staff = requestor is not None and requestor.role in ("ADMIN", "COORDINATOR")
            is_leader = team.leader_user_id == requesting_user_id
            is_self = user_id == requesting_user_id
            if not (is_staff or is_leader or is_self):
                raise DomainError(
                    UNAUTHORIZED,
                    "Only the team leader, the member themselves, or an admin can remove a member.",
                )
            if not is_staff and team.status == TeamStatus.LOCKED.value:
                raise DomainError(
                    TEAM_LOCKED,
                    "Cannot remove members from a locked team.",
                )

        target = next((r for r in team.members if r.user_id == user_id), None)
        if target is None:
            raise DomainError(
                "NOT_A_MEMBER",
                "User is not a member of this team.",
            )

        remaining = [r for r in team.members if r.user_id != user_id]

        # Delete the registration
        await self.registrations.delete(target.id)

        if not remaining:
            # Last member removed — delete the team
            await self.teams.delete(team_id)
            return None

        # If the removed member was the leader, promote another
        if target.member_role == TeamMemberRole.LEADER.value:
            new_leader = remaining[0]
            for r in remaining:
                r.member_role = TeamMemberRole.MEMBER.value
            new_leader.member_role = TeamMemberRole.LEADER.value
            team.leader_user_id = new_leader.user_id

            leader_user = await self.users.get(new_leader.user_id)
            if leader_user is not None:
                team.leader_contact_phone_snapshot = leader_user.phone
                team.leader_contact_email_snapshot = leader_user.email

        team.member_count = len(remaining)
        await self.session.flush()
        await self.session.refresh(team)
        return team

    async def delete_team(self, team_id: UUID) -> None:
        """Delete a team and all its member registrations."""
        team = await self.teams.get(team_id)
        if team is None:
            raise DomainError(TEAM_NOT_FOUND, "Team not found.")
        members = await self.registrations.list_by_team(team_id)
        for reg in members:
            await self.registrations.delete(reg.id)
        await self.teams.delete(team_id)

    # ========================================================
    # On-spot bulk register
    # ========================================================

    async def bulk_register_by_shackles_ids(
        self,
        event_id: UUID,
        team_name: str,
        shackles_ids: list[str],
        leader_shackles_id: str,
        *,
        lock: bool = True,
        mark_attended: bool = False,
        station_id: str | None = None,
    ) -> Team:
        """On-spot bulk registration from a list of Shackles IDs."""
        event = await self._load_and_validate_team_event(event_id)

        normalized_ids = list(dict.fromkeys(
            sid.strip().upper() for sid in shackles_ids if sid and sid.strip()
        ))
        if not normalized_ids:
            raise DomainError(
                "INVALID_INPUT",
                "At least one Shackles ID is required.",
            )

        leader_id = leader_shackles_id.strip().upper()
        if leader_id not in normalized_ids:
            raise DomainError(
                "INVALID_LEADER",
                "Leader Shackles ID must be in the roster.",
            )

        users = await self.users.get_by_shackles_ids(normalized_ids)
        by_shackles = {u.shackles_id: u for u in users if u.shackles_id}

        missing = [sid for sid in normalized_ids if sid not in by_shackles]
        if missing:
            raise DomainError(
                USER_NOT_FOUND,
                f"Unknown Shackles IDs: {', '.join(missing)}",
                {"missing": missing},
            )

        for sid in normalized_ids:
            user = by_shackles[sid]
            payment = await self.payments.get_by_user_id(user.id)
            if (
                payment is None
                or payment.status != "VERIFIED"
                or payment.year != settings.active_year
            ):
                raise DomainError(
                    PAYMENT_NOT_VERIFIED,
                    f"Payment not verified for {sid}.",
                )
            if not _package_allows_category(payment.package_type, event.category):
                raise DomainError(
                    PACKAGE_NOT_ALLOWED,
                    f"Package for {sid} does not allow this event category.",
                )

        normalized_name = _normalize_team_name(team_name)
        name_error = _validate_team_name(team_name, normalized_name)
        if name_error:
            raise DomainError("INVALID_TEAM_NAME", name_error)

        team = await self.teams.get_by_event_and_name(event.id, normalized_name)
        if team is None:
            team_code = await self._generate_unique_team_code(event.id)
            leader_user = by_shackles[leader_id]
            team = await self.teams.create(
                event_id=event.id,
                name=team_name.strip(),
                name_normalized=normalized_name,
                team_code=team_code,
                status=TeamStatus.OPEN.value,
                leader_user_id=leader_user.id,
                leader_contact_phone_snapshot=leader_user.phone,
                leader_contact_email_snapshot=leader_user.email,
                member_count=0,
            )

        for sid in normalized_ids:
            user = by_shackles[sid]
            if await self.registrations.is_registered(user.id, event.id):
                raise DomainError(
                    ALREADY_REGISTERED,
                    f"{sid} is already registered for this event.",
                )

        max_size = event.team_max_size or 4
        existing_members = await self.registrations.count_by_team(team.id)
        if existing_members + len(normalized_ids) > max_size:
            raise DomainError(
                TEAM_ABOVE_MAX_SIZE,
                f"Team would exceed the max size of {max_size}.",
            )

        now = datetime.now(timezone.utc)
        for sid in normalized_ids:
            user = by_shackles[sid]
            member_role = (
                TeamMemberRole.LEADER.value
                if sid == leader_id
                else TeamMemberRole.MEMBER.value
            )
            await self.registrations.create(
                user_id=user.id,
                event_id=event.id,
                team_id=team.id,
                member_role=member_role,
                team_name=team.name,
                team_size=1,
                attended=mark_attended,
                attended_at=now if mark_attended else None,
                source=RegistrationSource.ON_SPOT.value,
                sync_status=RegistrationSyncStatus.APPLIED.value,
                station_id=station_id,
                year=settings.active_year,
            )

        new_count = existing_members + len(normalized_ids)
        await self.teams.set_member_count(team.id, new_count)

        if lock or new_count >= max_size:
            min_size = event.team_min_size or 2
            if new_count >= min_size:
                await self.teams.try_lock(team.id, locked_by=str(by_shackles[leader_id].id))

        refreshed = await self.teams.get(team.id)
        if refreshed is None:
            raise DomainError(TEAM_NOT_FOUND, "Team not found after bulk register.")
        return refreshed

    # ========================================================
    # Reads
    # ========================================================

    async def list_teams_for_event(
        self,
        event_id: UUID,
        *,
        status: TeamStatus | None = None,
    ) -> list[Team]:
        """List teams for an event."""
        return await self.teams.list_by_event(event_id, status=status)

    async def list_my_teams(self, user_id: UUID) -> list[Team]:
        """List all teams where this user is a member or leader."""
        regs = await self.registrations.list_by_user(
            user_id, year=settings.active_year
        )
        team_ids = [reg.team_id for reg in regs if reg.team_id is not None]
        teams: list[Team] = []
        seen: set[UUID] = set()
        for tid in team_ids:
            if tid in seen:
                continue
            seen.add(tid)
            t = await self.teams.get(tid)
            if t is not None:
                teams.append(t)
        return teams

    async def get_team_with_members(self, team_id: UUID) -> Team:
        """Fetch a team with members. Raises if not found."""
        return await self.teams.get_with_members_or_raise(team_id)

    # ========================================================
    # Private helpers
    # ========================================================

    async def _load_and_validate_team_event(self, event_id: UUID) -> Event:
        event = await self.events.get(event_id)
        if event is None:
            raise DomainError(EVENT_NOT_FOUND, "Event not found.")
        if event.year != settings.active_year:
            raise DomainError(EVENT_WRONG_YEAR, "Event is not in the active year.")
        if event.is_archived or event.is_template or not event.is_active:
            raise DomainError(EVENT_INACTIVE, "Event is not open for registration.")
        if event.participation_mode != EventParticipationMode.TEAM.value:
            raise DomainError(NOT_TEAM_EVENT, "This event is not a team event.")
        return event

    async def _load_and_validate_user(self, user_id: UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise DomainError(USER_NOT_FOUND, "User not found.")
        payment = await self.payments.get_by_user_id(user_id)
        if payment is None or payment.status != "VERIFIED":
            raise DomainError(PAYMENT_NOT_VERIFIED, "Payment must be verified.")
        if payment.year != settings.active_year:
            raise DomainError(
                PAYMENT_NOT_VERIFIED, "Payment is not valid for the current year."
            )
        return user

    async def _check_package_allows(
        self, user_id: UUID, event: Event
    ) -> None:
        payment = await self.payments.get_by_user_id(user_id)
        if payment is None or payment.package_type is None:
            raise DomainError(NO_VERIFIED_PACKAGE, "No verified package found.")
        if not _package_allows_category(payment.package_type, event.category):
            raise DomainError(
                PACKAGE_NOT_ALLOWED,
                "Your package does not allow this event category.",
            )

    async def _check_time_clash(self, user_id: UUID, new_event: Event) -> None:
        if new_event.is_all_day or new_event.date is None or new_event.end_date is None:
            return
        existing = await self.registrations.list_by_user(
            user_id, year=settings.active_year
        )
        for reg in existing:
            e = reg.event
            if e.is_all_day or e.date is None or e.end_date is None:
                continue
            if new_event.date < e.end_date and new_event.end_date > e.date:
                raise DomainError(
                    TIME_CLASH,
                    f"Time conflict with '{e.name}'.",
                    {"conflicting_event_name": e.name},
                )

    async def _generate_unique_team_code(self, event_id: UUID) -> str:
        for _ in range(10):
            code = "".join(
                secrets.choice(_TEAM_CODE_ALPHABET) for _ in range(6)
            )
            if not await self.teams.team_code_exists(event_id, code):
                return code
        return secrets.token_hex(4).upper()

    async def _generate_unique_join_code(self) -> str:
        for _ in range(10):
            code = "".join(
                secrets.choice(_JOIN_CODE_ALPHABET) for _ in range(8)
            )
            if not await self.teams.join_code_exists(code):
                return code
        return secrets.token_hex(4).upper()


# ============================================================
# Pure helpers
# ============================================================

def _normalize_team_name(name: str) -> str:
    return " ".join(name.strip().split()).upper()


def _validate_team_name(name: str, normalized: str) -> str | None:
    """Return an error message, or None if valid."""
    import re

    if not re.match(r"^[A-Z0-9 _-]{3,40}$", normalized):
        return (
            "Team name must be 3-40 characters and contain only "
            "letters, numbers, spaces, hyphens, or underscores."
        )
    for word in _TEAM_NAME_BANNED:
        if word in normalized.split():
            return "Please choose a professional team name."
    return None


def _package_allows_category(
    package_type: str | None, category: str | None
) -> bool:
    if category is None:
        return True
    if package_type == "COMBO":
        return True
    if package_type == "EVENT_ONLY":
        return category == "EVENT"
    if package_type == "WORKSHOP_ONLY":
        return category == "WORKSHOP"
    return False