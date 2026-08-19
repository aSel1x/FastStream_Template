from typing import final
from uuid import UUID

from application.user.rbac_service import RBACService
from domain.user.entities.rbac import Permission
from domain.user.interfaces.persistence.readers import RoleReadDTO, RoleReader
from domain.user.value_objects import UserID


@final
class GetUserRolesUseCase:
    def __init__(self, role_reader: RoleReader) -> None:
        self._role_reader = role_reader

    async def __call__(self, user_id: UUID) -> list[RoleReadDTO]:
        return await self._role_reader.get_user_roles(UserID(user_id))


@final
class CheckPermissionUseCase:
    def __init__(self, role_reader: RoleReader) -> None:
        self._role_reader = role_reader

    async def __call__(self, user_id: UUID, permission: str) -> bool:
        roles = await self._role_reader.get_user_roles(UserID(user_id))
        return any(permission in r.permissions for r in roles)


@final
class GetAllRolesUseCase:
    def __init__(self, role_reader: RoleReader) -> None:
        self._role_reader = role_reader

    async def __call__(self) -> list[RoleReadDTO]:
        return await self._role_reader.get_all_roles()


@final
class ListPermissionsUseCase:
    def __init__(self, rbac_service: RBACService) -> None:
        self._rbac_service = rbac_service

    async def __call__(self) -> list[Permission]:
        return await self._rbac_service.get_all_permissions()
