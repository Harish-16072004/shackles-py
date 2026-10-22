"""add payment event registration indexes

Revision ID: e49d971d867d
Revises: b84512f68d1b
Create Date: 2026-10-05 15:30:39.650392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e49d971d867d'
down_revision: Union[str, Sequence[str], None] = 'b84512f68d1b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Payment indexes
    op.create_index(
        "Payment_captureSource_status_createdAt_idx",
        "Payment",
        ["captureSource", "status", "createdAt"],
        unique=False,
    )
    op.create_index(
        "Payment_paymentChannel_status_createdAt_idx",
        "Payment",
        ["paymentChannel", "status", "createdAt"],
        unique=False,
    )
    op.create_index(
        "Payment_status_year_idx",
        "Payment",
        ["status", "year"],
        unique=False,
    )

    # EventRegistration indexes
    op.create_index(
        "EventRegistration_year_eventId_idx",
        "EventRegistration",
        ["year", "eventId"],
        unique=False,
    )
    op.create_index(
        "EventRegistration_eventId_source_idx",
        "EventRegistration",
        ["eventId", "source"],
        unique=False,
    )
    op.create_index(
        "EventRegistration_eventId_teamId_idx",
        "EventRegistration",
        ["eventId", "teamId"],
        unique=False,
    )
    op.create_index(
        "EventRegistration_userId_idx",
        "EventRegistration",
        ["userId"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("EventRegistration_userId_idx", table_name="EventRegistration")
    op.drop_index("EventRegistration_eventId_teamId_idx", table_name="EventRegistration")
    op.drop_index("EventRegistration_eventId_source_idx", table_name="EventRegistration")
    op.drop_index("EventRegistration_year_eventId_idx", table_name="EventRegistration")
    op.drop_index("Payment_status_year_idx", table_name="Payment")
    op.drop_index("Payment_paymentChannel_status_createdAt_idx", table_name="Payment")
    op.drop_index("Payment_captureSource_status_createdAt_idx", table_name="Payment")