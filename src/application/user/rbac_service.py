from typing import final

from domain.user.entities.rbac import Permission, Role, UserRole
from domain.user.entities.user import User
from domain.user.exceptions import (
    PermissionDeniedError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
    UserNotFoundError,
)
from domain.user.interfaces import (
    PermissionRepositoryInterface,
    RoleRepositoryInterface,
    UserRepositoryInterface,
    UserRoleRepositoryInterface,
)
from domain.user.value_objects import RoleID, RoleName, UserID


@final
class RBACService:
    DEFAULT_ROLE_USER = 'user'
    DEFAULT_ROLE_ADMIN = 'admin'

    def __init__(
        self,
        user_repo: UserRepositoryInterface,
        role_repo: RoleRepositoryInterface,
        permission_repo: PermissionRepositoryInterface,
        user_role_repo: UserRoleRepositoryInterface,
    ) -> None:
        self._user_repo = user_repo
        self._role_repo = role_repo
        self._permission_repo = permission_repo
        self._user_role_repo = user_role_repo

    async def create_role(
        self,
        name: RoleName,
        description: str | None = None,
    ) -> Role:
        existing_role = await self._role_repo.acquire_by_name(name)
        if existing_role:
            raise RoleAlreadyExistsError(name.to_raw())

        role = Role.create(name=name, description=description)
        await self._role_repo.add(role)
        return role

    async def delete_role(
        self,
        role_id: RoleID,
    ) -> Role:
        role = await self._role_repo.acquire_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id.to_raw()))
        if role.name.to_raw() == self.DEFAULT_ROLE_ADMIN:
            raise PermissionDeniedError('Cannot delete admin role')

        deleted_role = role.delete()
        await self._role_repo.delete(role_id)
        return deleted_role

    async def assign_role(
        self,
        user_id: UserID,
        role_id: RoleID,
        assigned_by: UserID | None = None,
    ) -> User:
        user = await self._user_repo.acquire_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id.to_raw()))

        role = await self._role_repo.acquire_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id.to_raw()))

        existing = await self._user_role_repo.acquire_by_user_and_role(user_id, role_id)
        if existing:
            return user

        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
        )
        await self._user_role_repo.add(user_role)

        return user.assign_role(role_id, assigned_by)

    async def revoke_role(
        self,
        user_id: UserID,
        role_id: RoleID,
    ) -> User:
        user = await self._user_repo.acquire_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id.to_raw()))

        role = await self._role_repo.acquire_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id.to_raw()))

        if role.name.to_raw() == self.DEFAULT_ROLE_ADMIN:
            raise PermissionDeniedError('Cannot revoke admin role from user')

        await self._user_role_repo.delete(user_id, role_id)

        return user.revoke_role(role_id)

    async def get_user_roles(self, user_id: UserID) -> list[Role]:
        user_roles = await self._user_role_repo.acquire_by_user_id(user_id)
        roles: list[Role] = []
        for ur in user_roles:
            role = await self._role_repo.acquire_by_id(ur.role_id)
            if role:
                roles.append(role)
        return roles

    async def has_permission(self, user_id: UserID, permission: str) -> bool:
        roles = await self.get_user_roles(user_id)

        for role in roles:
            if role.has_permission(permission):
                return True
        return False

    async def require_permission(self, user_id: UserID, permission: str) -> None:
        if not await self.has_permission(user_id, permission):
            raise PermissionDeniedError(permission)

    async def add_permission_to_role(
        self,
        role_id: RoleID,
        permission_name: str,
    ) -> Role:
        role = await self._role_repo.acquire_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id.to_raw()))

        permission = await self._permission_repo.acquire_by_name(permission_name)
        if permission is None:
            permission = Permission(name=permission_name)
            await self._permission_repo.add(permission)

        updated_role = role.add_permission(permission)
        await self._role_repo.update(updated_role)
        return updated_role

    async def remove_permission_from_role(
        self,
        role_id: RoleID,
        permission_name: str,
    ) -> Role:
        role = await self._role_repo.acquire_by_id(role_id)
        if role is None:
            raise RoleNotFoundError(str(role_id.to_raw()))

        updated_role = role.remove_permission(permission_name)
        await self._role_repo.update(updated_role)
        return updated_role

    async def get_all_roles(self) -> list[Role]:
        return await self._role_repo.get_all()

    async def get_all_permissions(self) -> list[Permission]:
        return await self._permission_repo.get_all()