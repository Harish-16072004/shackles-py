"""RolePermission schemas."""

from pydantic import Field

from shackles.models.enums import Permission, Role
from shackles.schemas.common import ApiBase, ApiWrite


class RolePermissionCreate(ApiWrite):
    """Payload for adding a role-permission mapping."""

    role: Role
    permission: Permission


class RolePermissionRead(ApiBase):
    """Public role-permission representation."""

    role: Role
    permission: Permission


class RolePermissionMatrix(ApiBase):
    """Role → list of permissions."""

    role: Role
    permissions: list[Permission] = Field(default_factory=list)