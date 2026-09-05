from datetime import datetime
from typing import ClassVar, final, override
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from domain.user.entities.session import DeviceInfo
from domain.user.interfaces.persistence.readers import (
    RoleReadDTO,
    RoleReader,
    SessionReadDTO,
    SessionReader,
    UserReadDTO,
    UserReader,
)
from domain.user.value_objects import AccountLockInfo, UserID
from infrastructure.db.sqlalchemy.models.rbac import (
    PERMISSION_NAME_COLUMN,
    PERMISSIONS_TABLE,
    ROLE_PERMISSIONS_TABLE,
    ROLES_TABLE,
    USER_ROLES_TABLE,
)
from infrastructure.db.sqlalchemy.models.session import SESSIONS_TABLE
from infrastructure.db.sqlalchemy.models.user import USERS_TABLE
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import ColumnElement, FromClause


class _UserSummaryRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: UUID
    username: str
    email: str | None
    is_email_verified: bool
    is_locked: bool
    lock_until: datetime | None
    two_factor_secret: bytes | None
    two_factor_enabled_at: datetime | None


class _SessionSummaryRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    session_id: UUID
    created_at: datetime
    expires_at: datetime
    is_revoked: bool
    user_agent: str | None
    ip_address: str | None
    device_name: str | None
    browser: str | None
    os: str | None
    is_mobile: bool


class _RoleWithPermissionRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: UUID
    name: str
    description: str | None
    permission_name: str | None


@final
class SQLAlchemyUserReader(UserReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def get_by_id(self, user_id: UserID) -> UserReadDTO | None:
        result = await self._session.execute(
            select(USERS_TABLE).where(USERS_TABLE.c.id == user_id.to_raw())
        )
        mapping = result.mappings().first()
        if not mapping:
            return None
        row = _UserSummaryRow.model_validate(mapping)
        lock_info = AccountLockInfo(is_locked=row.is_locked, lock_until=row.lock_until)
        return UserReadDTO(
            user_id=row.id,
            username=row.username,
            email=row.email,
            is_email_verified=row.is_email_verified,
            is_locked=lock_info.is_locked_out(),
            # Only whether 2FA is on. A read model has no business carrying the seed.
            has_two_factor=bool(row.two_factor_secret and row.two_factor_enabled_at),
        )


@final
class SQLAlchemySessionReader(SessionReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def get_by_user_id(self, user_id: UserID) -> list[SessionReadDTO]:
        rows = await self._session.execute(
            select(SESSIONS_TABLE).where(
                and_(
                    SESSIONS_TABLE.c.user_id == user_id.to_raw(),
                    SESSIONS_TABLE.c.is_revoked.is_(False),
                )
            )
        )
        result: list[SessionReadDTO] = []
        for mapping in rows.mappings().all():
            row = _SessionSummaryRow.model_validate(mapping)
            result.append(
                SessionReadDTO(
                    session_id=row.session_id,
                    created_at=row.created_at,
                    expires_at=row.expires_at,
                    is_revoked=row.is_revoked,
                    device_info=DeviceInfo(
                        user_agent=row.user_agent,
                        ip_address=row.ip_address,
                        device_name=row.device_name,
                        browser=row.browser,
                        os=row.os,
                        is_mobile=row.is_mobile,
                    ),
                )
            )
        return result


@final
class SQLAlchemyRoleReader(RoleReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def get_user_roles(self, user_id: UserID) -> list[RoleReadDTO]:
        # One query, not 1 + 2N. This runs on every admin request through `require_admin`,
        # so the loop it replaces was the single hottest N+1 in the service.
        return await self._roles_with_permissions(
            ROLES_TABLE.join(
                USER_ROLES_TABLE,
                USER_ROLES_TABLE.c.role_id == ROLES_TABLE.c.id,
            ),
            USER_ROLES_TABLE.c.user_id == user_id.to_raw(),
        )

    @override
    async def get_all_roles(self) -> list[RoleReadDTO]:
        return await self._roles_with_permissions(ROLES_TABLE, None)

    async def _roles_with_permissions(
        self,
        source: FromClause,
        condition: ColumnElement[bool] | None,
    ) -> list[RoleReadDTO]:
        statement = (
            select(
                ROLES_TABLE.c.id,
                ROLES_TABLE.c.name,
                ROLES_TABLE.c.description,
                PERMISSION_NAME_COLUMN.label('permission_name'),
            )
            .select_from(
                source.outerjoin(
                    ROLE_PERMISSIONS_TABLE,
                    ROLE_PERMISSIONS_TABLE.c.role_id == ROLES_TABLE.c.id,
                ).outerjoin(
                    PERMISSIONS_TABLE,
                    PERMISSIONS_TABLE.c.id == ROLE_PERMISSIONS_TABLE.c.permission_id,
                )
            )
            .order_by(ROLES_TABLE.c.name)
        )
        if condition is not None:
            statement = statement.where(condition)

        rows = await self._session.execute(statement)
        roles: dict[UUID, RoleReadDTO] = {}
        permissions: dict[UUID, list[str]] = {}
        for mapping in rows.mappings().all():
            row = _RoleWithPermissionRow.model_validate(mapping)
            if row.id not in roles:
                roles[row.id] = RoleReadDTO(
                    role_id=row.id,
                    name=row.name,
                    description=row.description,
                    permissions=(),
                )
                permissions[row.id] = []
            if row.permission_name is not None:
                permissions[row.id].append(row.permission_name)

        return [
            RoleReadDTO(
                role_id=role.role_id,
                name=role.name,
                description=role.description,
                permissions=tuple(permissions[role.role_id]),
            )
            for role in roles.values()
        ]
