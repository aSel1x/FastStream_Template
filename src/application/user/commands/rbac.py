from typing import final
from dataclasses import dataclass
from uuid import UUID

from application.common.interfaces import UnitOfWorkInterface
from application.user.rbac_service import RBACService
from domain.user.entities.rbac import Role
from domain.user.value_objects import RoleID, RoleName, UserID


@dataclass
class CreateRoleInput:
    name: str
    description: str | None = None


@dataclass
class DeleteRoleInput:
    role_id: UUID


@dataclass
class AssignRoleInput:
    user_id: UUID
    role_id: UUID
    assigned_by: UUID | None = None


@dataclass
class RevokeRoleInput:
    user_id: UUID
    role_id: UUID


@dataclass
class AddPermissionToRoleInput:
    role_id: UUID
    permission_name: str


@dataclass
class RemovePermissionFromRoleInput:
    role_id: UUID
    permission_name: str


@dataclass
class RoleOutput:
    role_id: UUID
    name: str
    description: str | None
    permissions: tuple[str, ...]

    @classmethod
    def from_role(cls, role: Role) -> 'RoleOutput':
        return cls(
            role_id=role.role_id.to_raw(),
            name=role.name.to_raw(),
            description=role.description,
            permissions=tuple(p.name for p in role.permissions),
        )


@final
class AssignRoleUseCase:
    def __init__(
        self,
        rbac_service: RBACService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._rbac_service = rbac_service
        self._uow = uow

    async def __call__(self, input: AssignRoleInput) -> None:
        user = await self._rbac_service.assign_role(
            user_id=UserID(input.user_id),
            role_id=RoleID(input.role_id),
            assigned_by=UserID(input.assigned_by) if input.assigned_by else None,
        )
        self._uow.add_events(user.pull_events())
        await self._uow.commit()


@final
class RevokeRoleUseCase:
    def __init__(
        self,
        rbac_service: RBACService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._rbac_service = rbac_service
        self._uow = uow

    async def __call__(self, input: RevokeRoleInput) -> None:
        user = await self._rbac_service.revoke_role(
            user_id=UserID(input.user_id),
            role_id=RoleID(input.role_id),
        )
        self._uow.add_events(user.pull_events())
        await self._uow.commit()


@final
class CreateRoleUseCase:
    def __init__(
        self,
        rbac_service: RBACService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._rbac_service = rbac_service
        self._uow = uow

    async def __call__(self, input: CreateRoleInput) -> RoleOutput:
        role = await self._rbac_service.create_role(RoleName(input.name), input.description)
        self._uow.add_events(role.pull_events())
        await self._uow.commit()
        return RoleOutput.from_role(role)


@final
class DeleteRoleUseCase:
    def __init__(
        self,
        rbac_service: RBACService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._rbac_service = rbac_service
        self._uow = uow

    async def __call__(self, input: DeleteRoleInput) -> None:
        role = await self._rbac_service.delete_role(RoleID(input.role_id))
        self._uow.add_events(role.pull_events())
        await self._uow.commit()


@final
class AddPermissionToRoleUseCase:
    def __init__(
        self,
        rbac_service: RBACService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._rbac_service = rbac_service
        self._uow = uow

    async def __call__(self, input: AddPermissionToRoleInput) -> RoleOutput:
        role = await self._rbac_service.add_permission_to_role(
            RoleID(input.role_id), input.permission_name
        )
        self._uow.add_events(role.pull_events())
        await self._uow.commit()
        return RoleOutput.from_role(role)


@final
class RemovePermissionFromRoleUseCase:
    def __init__(
        self,
        rbac_service: RBACService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._rbac_service = rbac_service
        self._uow = uow

    async def __call__(self, input: RemovePermissionFromRoleInput) -> RoleOutput:
        role = await self._rbac_service.remove_permission_from_role(
            RoleID(input.role_id), input.permission_name
        )
        self._uow.add_events(role.pull_events())
        await self._uow.commit()
        return RoleOutput.from_role(role)
