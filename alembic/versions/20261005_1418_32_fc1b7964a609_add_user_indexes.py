"""add user indexes

Revision ID: fc1b7964a609
Revises: fd4c608e2e29
Create Date: 2026-10-05 14:18:32.244092

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc1b7964a609'
down_revision: Union[str, Sequence[str], None] = 'fd4c608e2e29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "User_role_idx",
        "User",
        ["role"],
        unique=False,
    )
    op.create_index(
        "User_createdAt_idx",
        "User",
        ["createdAt"],
        unique=False,
    )
    op.create_index(
        "User_registrationType_role_idx",
        "User",
        ["registrationType", "role"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("User_registrationType_role_idx", table_name="User")
    op.drop_index("User_createdAt_idx", table_name="User")
    op.drop_index("User_role_idx", table_name="User")
