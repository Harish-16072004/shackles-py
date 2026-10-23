"""add team invite staff onspot accommodation

Revision ID: 6cfe8dec339d
Revises: e49d971d867d
Create Date: 2026-10-05 15:45:14.934342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6cfe8dec339d'
down_revision: Union[str, Sequence[str], None] = 'e49d971d867d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('Accommodation',
    sa.Column('days', postgresql.ARRAY(sa.String()), nullable=False),
    sa.Column('userId', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['userId'], ['User.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('userId')
    )
    op.create_table('EventStaffAssignment',
    sa.Column('staffRole', sa.String(length=20), nullable=False),
    sa.Column('eventId', sa.UUID(), nullable=False),
    sa.Column('userId', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['eventId'], ['Event.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['userId'], ['User.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('eventId', 'userId', 'staffRole', name='EventStaffAssignment_eventId_userId_staffRole_key')
    )
    op.create_index('EventStaffAssignment_eventId_userId_idx', 'EventStaffAssignment', ['eventId', 'userId'], unique=False)
    op.create_table('OnSpotProfile',
    sa.Column('stationId', sa.String(length=100), nullable=True),
    sa.Column('deviceId', sa.String(length=100), nullable=True),
    sa.Column('referralSource', sa.String(length=200), nullable=True),
    sa.Column('notes', sa.String(length=500), nullable=True),
    sa.Column('userId', sa.UUID(), nullable=False),
    sa.Column('createdByUserId', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['createdByUserId'], ['User.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['userId'], ['User.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('userId')
    )
    op.create_index('OnSpotProfile_stationId_idx', 'OnSpotProfile', ['stationId'], unique=False)
    op.create_table('Team',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('nameNormalized', sa.String(length=200), nullable=False),
    sa.Column('teamCode', sa.String(length=20), nullable=False),
    sa.Column('joinCode', sa.String(length=20), nullable=True),
    sa.Column('joinCodeExpiresAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('memberCount', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('lockedAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('lockedBy', sa.String(length=50), nullable=True),
    sa.Column('cancelledAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('leaderContactPhoneSnapshot', sa.String(length=20), nullable=True),
    sa.Column('leaderContactEmailSnapshot', sa.String(length=255), nullable=True),
    sa.Column('eventId', sa.UUID(), nullable=False),
    sa.Column('leaderUserId', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['eventId'], ['Event.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['leaderUserId'], ['User.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('eventId', 'nameNormalized', name='Team_eventId_nameNormalized_key'),
    sa.UniqueConstraint('eventId', 'teamCode', name='Team_eventId_teamCode_key'),
    sa.UniqueConstraint('joinCode')
    )
    op.create_index('Team_eventId_status_idx', 'Team', ['eventId', 'status'], unique=False)
    op.create_index('Team_joinCode_idx', 'Team', ['joinCode'], unique=False)
    op.create_index('Team_leaderUserId_idx', 'Team', ['leaderUserId'], unique=False)
    op.create_table('TeamInvite',
    sa.Column('token', sa.String(length=100), nullable=False),
    sa.Column('invitedEmail', sa.String(length=255), nullable=True),
    sa.Column('expiresAt', sa.DateTime(timezone=True), nullable=False),
    sa.Column('usedAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('teamId', sa.UUID(), nullable=False),
    sa.Column('invitedByUserId', sa.UUID(), nullable=False),
    sa.Column('usedByUserId', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['invitedByUserId'], ['User.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['teamId'], ['Team.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['usedByUserId'], ['User.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token')
    )
    op.create_index('TeamInvite_invitedByUserId_idx', 'TeamInvite', ['invitedByUserId'], unique=False)
    op.create_index('TeamInvite_invitedEmail_idx', 'TeamInvite', ['invitedEmail'], unique=False)
    op.create_index('TeamInvite_teamId_idx', 'TeamInvite', ['teamId'], unique=False)
    op.create_foreign_key(
        'EventRegistration_teamId_fkey',
        'EventRegistration',
        'Team',
        ['teamId'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'EventRegistration_teamId_fkey',
        'EventRegistration',
        type_='foreignkey',
    )
    op.drop_index('TeamInvite_teamId_idx', table_name='TeamInvite')
    op.drop_index('TeamInvite_invitedEmail_idx', table_name='TeamInvite')
    op.drop_index('TeamInvite_invitedByUserId_idx', table_name='TeamInvite')
    op.drop_table('TeamInvite')
    op.drop_index('Team_leaderUserId_idx', table_name='Team')
    op.drop_index('Team_joinCode_idx', table_name='Team')
    op.drop_index('Team_eventId_status_idx', table_name='Team')
    op.drop_table('Team')
    op.drop_index('OnSpotProfile_stationId_idx', table_name='OnSpotProfile')
    op.drop_table('OnSpotProfile')
    op.drop_index('EventStaffAssignment_eventId_userId_idx', table_name='EventStaffAssignment')
    op.drop_table('EventStaffAssignment')
    op.drop_table('Accommodation')
