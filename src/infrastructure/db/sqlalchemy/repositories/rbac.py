from datetime import datetime
from typing import ClassVar, final, override

from pydantic import BaseModel, ConfigDict

from domain.user.entities.rbac import Permission, Role, UserRole
from domain.user.interfaces.persistence.rbac import (
    PermissionRepositoryInterface,
    RoleRepositoryInterface,
    UserRoleRepositoryInterface,
)
from domain.user.value_objects import RoleID, RoleName, UserID
from infrastructure.db.sqlalchemy.models.rbac import (
    PERMISSION_ID_COLUMN,
    PERMISSIONS_TABLE,
    ROLES_TABLE,
    ROLE_PERMISSIONS_TABLE,
    USER_ROLES_TABLE,
)
from infrastructure.db.sqlalchemy.repositories.base import SQLAlchemyRepo

from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_


class _PermissionRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: UUID
    name: str
    description: str | None


class _RoleRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: UUID
    name: str
    description: str | None


class _UserRoleRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    user_id: UUID
    role_id: UUID
    assigned_at: datetime
    assigned_by: UUID | None


@final
class SQLAlchemyPermissionRepo(SQLAlchemyRepo, PermissionRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    @override
    async def acquire_by_name(self, name: str) -> Permission | None:
        result = await self._session.execute(
            select(PERMISSIONS_TABLE).where(PERMISSIONS_TABLE.c.name == name)
        )
        mapping = result.mappings().first()
        if not mapping:
            return None
        row = _PermissionRow.model_validate(mapping)
        return Permission(
            name=row.name,
            description=row.description,
        )

    @override
    async def get_all(self) -> list[Permission]:
        result = await self._session.execute(select(PERMISSIONS_TABLE))
        return [
            Permission(name=row.name, description=row.description)
            for row in (_PermissionRow.model_validate(m) for m in result.mappings().all())
        ]

    @override
    async def add(self, permission: Permission) -> None:
        _ = await self._session.execute(PERMISSIONS_TABLE.insert().values(
            id=uuid4(),
            name=permission.name,
            description=permission.description,
        ))
        await self._session.flush()


@final
class SQLAlchemyRoleRepo(SQLAlchemyRepo, RoleRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    @override
    async def acquire_by_id(self, role_id: RoleID) -> Role | None:
        result = await self._session.execute(
            select(ROLES_TABLE).where(ROLES_TABLE.c.id == role_id.to_raw())
        )
        mapping = result.mappings().first()
        if not mapping:
            return None
        row = _RoleRow.model_validate(mapping)

        permissions = await self._get_role_permissions(row.id)

        return Role(
            role_id=RoleID(row.id),
            name=RoleName(row.name),
            description=row.description,
            permissions=tuple(permissions),
        )

    @override
    async def acquire_by_name(self, name: RoleName) -> Role | None:
        result = await self._session.execute(
            select(ROLES_TABLE).where(ROLES_TABLE.c.name == name.to_raw())
        )
        mapping = result.mappings().first()
        if not mapping:
            return None
        row = _RoleRow.model_validate(mapping)

        permissions = await self._get_role_permissions(row.id)

        return Role(
            role_id=RoleID(row.id),
            name=RoleName(row.name),
            description=row.description,
            permissions=tuple(permissions),
        )

    @override
    async def get_all(self) -> list[Role]:
        result = await self._session.execute(select(ROLES_TABLE))
        roles: list[Role] = []
        for mapping in result.mappings().all():
            row = _RoleRow.model_validate(mapping)
            permissions = await self._get_role_permissions(row.id)
            roles.append(Role(
                role_id=RoleID(row.id),
                name=RoleName(row.name),
                description=row.description,
                permissions=tuple(permissions),
            ))
        return roles

    @override
    async def add(self, role: Role) -> None:
        _ = await self._session.execute(ROLES_TABLE.insert().values(
            id=role.role_id.to_raw(),
            name=role.name.to_raw(),
            description=role.description,
        ))

        for perm in role.permissions:
            perm_exists = await self._session.scalar(
                select(PERMISSION_ID_COLUMN).where(PERMISSIONS_TABLE.c.name == perm.name)
            )
            if not perm_exists:
                _ = await self._session.execute(PERMISSIONS_TABLE.insert().values(
                    id=uuid4(),
                    name=perm.name,
                    description=perm.description,
                ))

            perm_result = await self._session.execute(
                select(PERMISSIONS_TABLE).where(PERMISSIONS_TABLE.c.name == perm.name)
            )
            perm_mapping = perm_result.mappings().first()
            if perm_mapping:
                perm_row = _PermissionRow.model_validate(perm_mapping)
                _ = await self._session.execute(ROLE_PERMISSIONS_TABLE.insert().values(
                    role_id=role.role_id.to_raw(),
                    permission_id=perm_row.id,
                ))

        await self._session.flush()

    @override
    async def update(self, role: Role) -> None:
        _ = await self._session.execute(
            ROLES_TABLE.update()
            .where(ROLES_TABLE.c.id == role.role_id.to_raw())
            .values(name=role.name.to_raw(), description=role.description)
        )

        role_id_raw = role.role_id.to_raw()
        current_ids = set(
            (await self._session.scalars(
                select(ROLE_PERMISSIONS_TABLE.c.permission_id).where(
                    ROLE_PERMISSIONS_TABLE.c.role_id == role_id_raw
                )
            )).all()
        )

        desired_ids: set[UUID] = set()
        for perm in role.permissions:
            perm_id = await self._session.scalar(
                select(PERMISSION_ID_COLUMN).where(PERMISSIONS_TABLE.c.name == perm.name)
            )
            if perm_id is None:
                perm_id = uuid4()
                _ = await self._session.execute(PERMISSIONS_TABLE.insert().values(
                    id=perm_id, name=perm.name, description=perm.description,
                ))
            desired_ids.add(perm_id)

        to_remove = current_ids - desired_ids
        if to_remove:
            _ = await self._session.execute(
                ROLE_PERMISSIONS_TABLE.delete().where(and_(
                    ROLE_PERMISSIONS_TABLE.c.role_id == role_id_raw,
                    ROLE_PERMISSIONS_TABLE.c.permission_id.in_(to_remove),
                ))
            )
        for perm_id in desired_ids - current_ids:
            _ = await self._session.execute(ROLE_PERMISSIONS_TABLE.insert().values(
                role_id=role_id_raw, permission_id=perm_id,
            ))

        await self._session.flush()

    @override
    async def delete(self, role_id: RoleID) -> None:
        role_id_raw = role_id.to_raw()
        _ = await self._session.execute(
            ROLE_PERMISSIONS_TABLE.delete().where(ROLE_PERMISSIONS_TABLE.c.role_id == role_id_raw)
        )
        _ = await self._session.execute(
            USER_ROLES_TABLE.delete().where(USER_ROLES_TABLE.c.role_id == role_id_raw)
        )
        _ = await self._session.execute(
            ROLES_TABLE.delete().where(ROLES_TABLE.c.id == role_id_raw)
        )
        await self._session.flush()

    async def _get_role_permissions(self, role_id: UUID) -> list[Permission]:
        result = await self._session.execute(
            select(PERMISSIONS_TABLE)
            .select_from(PERMISSIONS_TABLE.join(
                ROLE_PERMISSIONS_TABLE,
                PERMISSIONS_TABLE.c.id == ROLE_PERMISSIONS_TABLE.c.permission_id
            ))
            .where(ROLE_PERMISSIONS_TABLE.c.role_id == role_id)
        )
        return [
            Permission(name=row.name, description=row.description)
            for row in (_PermissionRow.model_validate(m) for m in result.mappings().all())
        ]


@final
class SQLAlchemyUserRoleRepo(SQLAlchemyRepo, UserRoleRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    @override
    async def acquire_by_user_id(self, user_id: UserID) -> list[UserRole]:
        result = await self._session.execute(
            select(USER_ROLES_TABLE).where(USER_ROLES_TABLE.c.user_id == user_id.to_raw())
        )
        return [
            UserRole(
                user_id=UserID(row.user_id),
                role_id=RoleID(row.role_id),
                assigned_at=row.assigned_at,
                assigned_by=UserID(row.assigned_by) if row.assigned_by else None,
            )
            for row in (_UserRoleRow.model_validate(m) for m in result.mappings().all())
        ]

    @override
    async def acquire_by_user_and_role(
        self, user_id: UserID, role_id: RoleID
    ) -> UserRole | None:
        result = await self._session.execute(
            select(USER_ROLES_TABLE).where(
                and_(
                    USER_ROLES_TABLE.c.user_id == user_id.to_raw(),
                    USER_ROLES_TABLE.c.role_id == role_id.to_raw(),
                )
            )
        )
        mapping = result.mappings().first()
        if not mapping:
            return None
        row = _UserRoleRow.model_validate(mapping)
        return UserRole(
            user_id=UserID(row.user_id),
            role_id=RoleID(row.role_id),
            assigned_at=row.assigned_at,
            assigned_by=UserID(row.assigned_by) if row.assigned_by else None,
        )

    @override
    async def add(self, user_role: UserRole) -> None:
        _ = await self._session.execute(USER_ROLES_TABLE.insert().values(
            user_id=user_role.user_id.to_raw(),
            role_id=user_role.role_id.to_raw(),
            assigned_at=user_role.assigned_at,
            assigned_by=user_role.assigned_by.to_raw() if user_role.assigned_by else None,
        ))
        await self._session.flush()

    @override
    async def delete(self, user_id: UserID, role_id: RoleID) -> None:
        _ = await self._session.execute(
            USER_ROLES_TABLE.delete().where(
                and_(
                    USER_ROLES_TABLE.c.user_id == user_id.to_raw(),
                    USER_ROLES_TABLE.c.role_id == role_id.to_raw(),
                )
            )
        )
        await self._session.flush()

    @override
    async def delete_by_user_id(self, user_id: UserID) -> None:
        _ = await self._session.execute(
            USER_ROLES_TABLE.delete().where(USER_ROLES_TABLE.c.user_id == user_id.to_raw())
        )
        await self._session.flush()
