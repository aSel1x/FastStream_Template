from datetime import datetime
from typing import ClassVar, final, override
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from domain.user.entities.session import DeviceInfo
from domain.user.interfaces.persistence.readers import (
    RoleReader,
    SessionReader,
    UserReader,
    UserReadDTO,
    SessionReadDTO,
    RoleReadDTO,
)
from domain.user.value_objects import AccountLockInfo, TwoFactorSecret, UserID
from infrastructure.db.sqlalchemy.models.rbac import (
    PERMISSION_NAME_COLUMN,
    PERMISSIONS_TABLE,
    ROLES_TABLE,
    ROLE_PERMISSIONS_TABLE,
    USER_ROLES_TABLE,
)
from infrastructure.db.sqlalchemy.models.session import SESSIONS_TABLE
from infrastructure.db.sqlalchemy.models.user import USERS_TABLE

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession


class _UserSummaryRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: UUID
    username: str
    email: str | None
    is_email_verified: bool
    is_locked: bool
    lock_until: datetime | None
    two_factor_secret: str | None
    two_factor_enabled_at: datetime | None
    two_factor_backup_codes: list[str] | None


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


class _UserRoleRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    role_id: UUID


class _RoleSummaryRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: UUID
    name: str
    description: str | None


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
        two_fa: TwoFactorSecret | None = None
        if row.two_factor_secret and row.two_factor_enabled_at:
            two_fa = TwoFactorSecret(
                secret=row.two_factor_secret,
                backup_codes=tuple(row.two_factor_backup_codes or ()),
                enabled_at=row.two_factor_enabled_at,
            )
        lock_info = AccountLockInfo(is_locked=row.is_locked, lock_until=row.lock_until)
        return UserReadDTO(
            user_id=row.id,
            username=row.username,
            email=row.email,
            is_email_verified=row.is_email_verified,
            is_locked=lock_info.is_locked_out(),
            two_factor_secret=two_fa,
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
            result.append(SessionReadDTO(
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
            ))
        return result


@final
class SQLAlchemyRoleReader(RoleReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def get_user_roles(self, user_id: UserID) -> list[RoleReadDTO]:
        user_roles = await self._session.execute(
            select(USER_ROLES_TABLE).where(
                USER_ROLES_TABLE.c.user_id == user_id.to_raw()
            )
        )
        roles: list[RoleReadDTO] = []
        for ur_mapping in user_roles.mappings().all():
            ur = _UserRoleRow.model_validate(ur_mapping)
            role_result = await self._session.execute(
                select(ROLES_TABLE).where(ROLES_TABLE.c.id == ur.role_id)
            )
            role_mapping = role_result.mappings().first()
            if not role_mapping:
                continue
            role_row = _RoleSummaryRow.model_validate(role_mapping)
            perms = await self._get_role_permissions(str(role_row.id))
            roles.append(RoleReadDTO(
                role_id=role_row.id,
                name=role_row.name,
                description=role_row.description,
                permissions=perms,
            ))
        return roles

    @override
    async def get_all_roles(self) -> list[RoleReadDTO]:
        rows = await self._session.execute(select(ROLES_TABLE))
        roles: list[RoleReadDTO] = []
        for mapping in rows.mappings().all():
            row = _RoleSummaryRow.model_validate(mapping)
            perms = await self._get_role_permissions(str(row.id))
            roles.append(RoleReadDTO(
                role_id=row.id,
                name=row.name,
                description=row.description,
                permissions=perms,
            ))
        return roles

    async def _get_role_permissions(self, role_id: str) -> tuple[str, ...]:
        result = await self._session.execute(
            select(PERMISSION_NAME_COLUMN)
            .select_from(PERMISSIONS_TABLE.join(
                ROLE_PERMISSIONS_TABLE,
                PERMISSIONS_TABLE.c.id == ROLE_PERMISSIONS_TABLE.c.permission_id,
            ))
            .where(ROLE_PERMISSIONS_TABLE.c.role_id == role_id)
        )
        return tuple(result.scalars().all())
