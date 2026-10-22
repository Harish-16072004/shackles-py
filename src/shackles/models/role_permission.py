"""RolePermission — maps roles to fine-grained permissions.

Composite primary key on (role, permission). No id column, no timestamps.
This is a lookup table.
"""

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from shackles.db.base import Base


class RolePermission(Base):
    """A role-permission mapping (composite PK)."""

    __tablename__ = "RolePermission"

    role: Mapped[str] = mapped_column(String(30), primary_key=True)
    permission: Mapped[str] = mapped_column(String(50), primary_key=True)

    # ---- Indexes ----
    __table_args__ = (
        Index("RolePermission_role_idx", "role"),
    )

    def __repr__(self) -> str:
        return f"<RolePermission {self.role}:{self.permission}>"