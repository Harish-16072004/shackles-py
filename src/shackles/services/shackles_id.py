"""Shackles ID allocation.

Format: `SH{YY}{TYPE}{NNN}` where:
  - YY is the last two digits of the year (e.g., '26' for 2026)
  - TYPE is 'G' (General), 'W' (Workshop), or 'C' (Combo)
  - NNN is the zero-padded sequence number

Example: `SH26G001`, `SH26W042`, `SH26C501`

Allocation is serialized via `SELECT ... FOR UPDATE` on the sequence row,
so concurrent calls produce unique IDs without needing serializable
transactions or retry loops.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shackles.errors import DomainError, INVALID_INPUT
from shackles.models.enums import RegistrationType
from shackles.models.shackles_id_sequence import ShacklesIdSequence


# Segment letter per registration type
_TYPE_SEGMENT = {
    RegistrationType.GENERAL.value: "G",
    RegistrationType.WORKSHOP.value: "W",
    RegistrationType.COMBO.value: "C",
}


def _format_shackles_id(
    year: int,
    registration_type: str,
    sequence: int,
) -> str:
    """Format the sequence number into a Shackles ID string."""
    year_short = str(year)[-2:]
    type_segment = _TYPE_SEGMENT.get(registration_type, "G")
    return f"SH{year_short}{type_segment}{sequence:03d}"


async def allocate_shackles_id(
    session: AsyncSession,
    year: int,
    registration_type: str,
    start_from: int = 1,
) -> str:
    """Allocate the next Shackles ID for (year, registration_type).

    Args:
        session: An active database session inside a transaction.
        year: The symposium year (e.g., 2026).
        registration_type: One of 'GENERAL', 'WORKSHOP', 'COMBO'.
        start_from: Floor for the sequence number. On-spot registrations
            use 500 to visually distinguish them from online ones.

    Returns:
        The formatted Shackles ID string.

    Raises:
        DomainError(INVALID_INPUT) if year or type is invalid.
    """
    if not isinstance(year, int) or year < 2000 or year > 3000:
        raise DomainError(
            INVALID_INPUT,
            f"Invalid year: {year}",
            {"year": year},
        )

    if registration_type not in _TYPE_SEGMENT:
        raise DomainError(
            INVALID_INPUT,
            f"Invalid registration type: {registration_type}",
            {"registration_type": registration_type},
        )

    # Lock the row for update (or discover it doesn't exist)
    stmt = (
        select(ShacklesIdSequence)
        .where(
            ShacklesIdSequence.year == year,
            ShacklesIdSequence.registration_type == registration_type,
        )
        .with_for_update()
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        # First allocation for this (year, type)
        row = ShacklesIdSequence(
            year=year,
            registration_type=registration_type,
            last_issued=start_from,
        )
        session.add(row)
        await session.flush()
        await session.refresh(row)
    else:
        # Subsequent allocation — bump the counter
        next_value = row.last_issued + 1
        if next_value < start_from:
            next_value = start_from
        row.last_issued = next_value
        await session.flush()
        await session.refresh(row)

    return _format_shackles_id(year, registration_type, row.last_issued)


async def peek_next_shackles_id(
    session: AsyncSession,
    year: int,
    registration_type: str,
    start_from: int = 1,
) -> str:
    """Preview the next ID without consuming it.

    Useful for dry-run previews in the UI ("your ID will be SH26G042").
    """
    stmt = select(ShacklesIdSequence).where(
        ShacklesIdSequence.year == year,
        ShacklesIdSequence.registration_type == registration_type,
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()

    if row is None:
        sequence = start_from
    else:
        sequence = max(row.last_issued + 1, start_from)

    return _format_shackles_id(year, registration_type, sequence)


async def get_sequence_state(
    session: AsyncSession,
    year: int,
) -> dict[str, int]:
    """Return the current last_issued value per registration type."""
    stmt = select(ShacklesIdSequence).where(ShacklesIdSequence.year == year)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return {row.registration_type: row.last_issued for row in rows}