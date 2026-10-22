"""RolePermissionRepository — data access for role → permission mappings."""

from sqlalchemy import delete, func, select

from shackles.models.enums import Permission, Role
from shackles.models.role_permission import RolePermission
from shackles.repositories.base import BaseRepository


class RolePermissionRepository(BaseRepository[RolePermission]):
    """Data access for role-permission mappings.

    This is a composite-primary-key table (role, permission). It does
    not inherit the standard id-based helpers. The overridden `get`,
    `update`, and `delete` methods raise NotImplementedError to prevent
    accidental misuse.
    """

    model = RolePermission

    # ========================================================
    # Lookups
    # ========================================================

    async def has_permission(
        self,
        role: Role | str,
        permission: Permission | str,
    ) -> bool:
        """Check whether a role has a specific permission."""
        role_value = role.value if isinstance(role, Role) else role
        perm_value = (
            permission.value if isinstance(permission, Permission) else permission
        )
        stmt = (
            select(func.count())
            .select_from(RolePermission)
            .where(
                RolePermission.role == role_value,
                RolePermission.permission == perm_value,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def list_permissions_for_role(
        self,
        role: Role | str,
    ) -> list[Permission]:
        """List all permissions granted to a role."""
        role_value = role.value if isinstance(role, Role) else role
        stmt = (
            select(RolePermission.permission)
            .where(RolePermission.role == role_value)
            .order_by(RolePermission.permission.asc())
        )
        result = await self.session.execute(stmt)
        return [Permission(p) for p in result.scalars().all()]

    async def list_roles_with_permission(
        self,
        permission: Permission | str,
    ) -> list[Role]:
        """List all roles that have a given permission."""
        perm_value = (
            permission.value if isinstance(permission, Permission) else permission
        )
        stmt = (
            select(RolePermission.role)
            .where(RolePermission.permission == perm_value)
            .order_by(RolePermission.role.asc())
        )
        result = await self.session.execute(stmt)
        return [Role(r) for r in result.scalars().all()]

    async def list_all(self) -> list[RolePermission]:
        """List every role-permission mapping."""
        stmt = select(RolePermission).order_by(
            RolePermission.role.asc(),
            RolePermission.permission.asc(),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ========================================================
    # Bulk operations
    # ========================================================

    async def upsert(
        self,
        role: Role | str,
        permission: Permission | str,
    ) -> RolePermission:
        """Add a role-permission mapping if not present.

        Idempotent: calling twice with the same args is a no-op on the
        second call.
        """
        role_value = role.value if isinstance(role, Role) else role
        perm_value = (
            permission.value if isinstance(permission, Permission) else permission
        )
        existing = await self.session.get(
            RolePermission, {"role": role_value, "permission": perm_value}
        )
        if existing is not None:
            return existing
        obj = RolePermission(role=role_value, permission=perm_value)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def bulk_upsert(
        self,
        mappings: list[tuple[Role | str, Permission | str]],
    ) -> int:
        """Upsert many mappings. Returns count of newly created rows."""
        created = 0
        for role, perm in mappings:
            role_value = role.value if isinstance(role, Role) else role
            perm_value = perm.value if isinstance(perm, Permission) else perm
            existing = await self.session.get(
                RolePermission,
                {"role": role_value, "permission": perm_value},
            )
            if existing is None:
                self.session.add(
                    RolePermission(role=role_value, permission=perm_value)
                )
                created += 1
        await self.session.flush()
        return created

    async def delete_for_role(self, role: Role | str) -> int:
        """Remove all permissions for a role. Returns count deleted."""
        role_value = role.value if isinstance(role, Role) else role
        stmt = delete(RolePermission).where(RolePermission.role == role_value)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount or 0

    async def delete_mapping(
        self,
        role: Role | str,
        permission: Permission | str,
    ) -> bool:
        """Remove a specific role-permission mapping."""
        role_value = role.value if isinstance(role, Role) else role
        perm_value = (
            permission.value if isinstance(permission, Permission) else permission
        )
        stmt = delete(RolePermission).where(
            RolePermission.role == role_value,
            RolePermission.permission == perm_value,
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return (result.rowcount or 0) > 0

    # ========================================================
    # Override base methods that don't fit a composite PK
    # ========================================================

    async def get(self, id):  # type: ignore[override]
        raise NotImplementedError(
            "RolePermission has a composite PK. "
            "Use has_permission or list_permissions_for_role."
        )

    async def update(self, id, **kwargs):  # type: ignore[override]
        raise NotImplementedError(
            "RolePermission is immutable. Delete + upsert instead."
        )

    async def delete(self, id) -> bool:  # type: ignore[override]
        raise NotImplementedError(
            "RolePermission uses composite PK. "
            "Use delete_mapping or delete_for_role."
        )