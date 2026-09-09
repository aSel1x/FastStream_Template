from typing import final
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, delete, get, post
from litestar.connection import Request
from litestar.datastructures.state import State
from litestar.params import FromPath
from litestar.security.jwt import Token
from litestar.status_codes import HTTP_200_OK
from pydantic import BaseModel

from application.user.commands.rbac import (
    AddPermissionToRoleInput,
    AddPermissionToRoleUseCase,
    AssignRoleInput,
    AssignRoleUseCase,
    CreateRoleInput,
    CreateRoleUseCase,
    DeleteRoleInput,
    DeleteRoleUseCase,
    RemovePermissionFromRoleInput,
    RemovePermissionFromRoleUseCase,
    RevokeRoleInput,
    RevokeRoleUseCase,
    RoleOutput,
)
from application.user.queries.rbac import (
    GetAllRolesUseCase,
    GetUserRolesUseCase,
    ListPermissionsUseCase,
)
from presentation.http.guards import require_admin
from presentation.http.security import UserSecuritySchema


class CreateRoleRequestSchema(BaseModel):
    name: str
    description: str | None = None


class RoleResponseSchema(BaseModel):
    role_id: str
    name: str
    description: str | None = None
    permissions: list[str] = []

    @classmethod
    def from_output(cls, role: RoleOutput) -> RoleResponseSchema:
        return cls(
            role_id=str(role.role_id),
            name=role.name,
            description=role.description,
            permissions=list(role.permissions),
        )


class AssignRoleRequestSchema(BaseModel):
    user_id: UUID


class PermissionRequestSchema(BaseModel):
    permission_name: str


class PermissionResponseSchema(BaseModel):
    name: str
    description: str | None = None


@final
class RolesController(Controller):
    path = '/admin/roles'
    guards = [require_admin]

    @post('/')
    @inject
    async def create_role(
        self,
        data: CreateRoleRequestSchema,
        use_case: FromDishka[CreateRoleUseCase],
    ) -> RoleResponseSchema:
        role = await use_case(CreateRoleInput(name=data.name, description=data.description))
        return RoleResponseSchema.from_output(role)

    @delete('/{role_id:uuid}')
    @inject
    async def delete_role(
        self,
        role_id: FromPath[UUID],
        use_case: FromDishka[DeleteRoleUseCase],
    ) -> None:
        await use_case(DeleteRoleInput(role_id=role_id))

    @get('/')
    @inject
    async def list_roles(
        self,
        use_case: FromDishka[GetAllRolesUseCase],
    ) -> list[RoleResponseSchema]:
        roles = await use_case()
        return [
            RoleResponseSchema(
                role_id=str(r.role_id),
                name=r.name,
                description=r.description,
                permissions=list(r.permissions),
            )
            for r in roles
        ]

    @post('/{role_id:uuid}/assign')
    @inject
    async def assign_role(
        self,
        role_id: FromPath[UUID],
        data: AssignRoleRequestSchema,
        request: Request[UserSecuritySchema, Token, State],
        use_case: FromDishka[AssignRoleUseCase],
    ) -> dict[str, str]:
        await use_case(
            AssignRoleInput(
                user_id=data.user_id,
                role_id=role_id,
                assigned_by=request.user.user_id,
            )
        )
        return {'message': 'Role assigned'}

    @post('/{role_id:uuid}/revoke')
    @inject
    async def revoke_role(
        self,
        role_id: FromPath[UUID],
        data: AssignRoleRequestSchema,
        use_case: FromDishka[RevokeRoleUseCase],
    ) -> dict[str, str]:
        await use_case(
            RevokeRoleInput(
                user_id=data.user_id,
                role_id=role_id,
            )
        )
        return {'message': 'Role revoked'}

    @get('/users/{user_id:uuid}')
    @inject
    async def get_user_roles(
        self,
        user_id: FromPath[UUID],
        use_case: FromDishka[GetUserRolesUseCase],
    ) -> list[RoleResponseSchema]:
        roles = await use_case(user_id)
        return [
            RoleResponseSchema(
                role_id=str(r.role_id),
                name=r.name,
                description=r.description,
                permissions=list(r.permissions),
            )
            for r in roles
        ]

    @post('/{role_id:uuid}/permissions')
    @inject
    async def add_permission(
        self,
        role_id: FromPath[UUID],
        data: PermissionRequestSchema,
        use_case: FromDishka[AddPermissionToRoleUseCase],
    ) -> RoleResponseSchema:
        role = await use_case(
            AddPermissionToRoleInput(
                role_id=role_id,
                permission_name=data.permission_name,
            )
        )
        return RoleResponseSchema.from_output(role)

    @delete('/{role_id:uuid}/permissions/{permission_name:str}', status_code=HTTP_200_OK)
    @inject
    async def remove_permission(
        self,
        role_id: FromPath[UUID],
        permission_name: FromPath[str],
        use_case: FromDishka[RemovePermissionFromRoleUseCase],
    ) -> RoleResponseSchema:
        role = await use_case(
            RemovePermissionFromRoleInput(
                role_id=role_id,
                permission_name=permission_name,
            )
        )
        return RoleResponseSchema.from_output(role)


@final
class PermissionsController(Controller):
    path = '/admin/permissions'
    guards = [require_admin]

    @get('/')
    @inject
    async def list_permissions(
        self,
        use_case: FromDishka[ListPermissionsUseCase],
    ) -> list[PermissionResponseSchema]:
        permissions = await use_case()
        return [
            PermissionResponseSchema(name=p.name, description=p.description) for p in permissions
        ]
