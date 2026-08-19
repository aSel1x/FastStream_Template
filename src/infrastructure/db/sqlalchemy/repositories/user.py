from datetime import datetime
from typing import ClassVar, final, override
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import exists, select

from domain.user.entities.user import User
from domain.user.interfaces import UserRepositoryInterface
from domain.user.value_objects import (
    AccountLockInfo,
    DeletionTime,
    Email,
    EmailVerification,
    HashedPassword,
    PasswordResetToken,
    TwoFactorSecret,
    UserID,
    Username,
)
from infrastructure.db.sqlalchemy.models.user import USER_ID_COLUMN, USERS_TABLE
from infrastructure.db.sqlalchemy.repositories.base import SQLAlchemyRepo


class _UserRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: UUID
    username: str
    email: str | None
    hashed_password: bytes
    deleted_at: datetime | None
    is_locked: bool
    locked_at: datetime | None
    lock_reason: str | None
    failed_attempts: int
    lock_until: datetime | None
    is_email_verified: bool
    email_verification_token: str | None
    email_verified_at: datetime | None
    email_verification_expires_at: datetime | None
    password_reset_token: str | None
    password_reset_created_at: datetime | None
    password_reset_expires_at: datetime | None
    password_reset_used: bool
    two_factor_secret: str | None
    two_factor_enabled_at: datetime | None
    two_factor_backup_codes: list[str] | None


_ColumnValue = UUID | str | bytes | bool | int | datetime | list[str] | None


def _row_to_user(mapping: RowMapping) -> User:
    row = _UserRow.model_validate(mapping)

    password_reset_token: PasswordResetToken | None = None
    if row.password_reset_token:
        password_reset_token = PasswordResetToken(
            token=row.password_reset_token,
            created_at=row.password_reset_created_at,
            expires_at=row.password_reset_expires_at,
            is_used=row.password_reset_used,
        )

    two_factor_secret: TwoFactorSecret | None = None
    if row.two_factor_secret:
        two_factor_secret = TwoFactorSecret(
            secret=row.two_factor_secret,
            backup_codes=tuple(row.two_factor_backup_codes or ()),
            enabled_at=row.two_factor_enabled_at,
        )

    return User(
        id=UserID(row.id),
        username=Username(row.username),
        email=Email(row.email),
        hashed_password=HashedPassword(row.hashed_password),
        deleted_at=DeletionTime(row.deleted_at),
        account_lock=AccountLockInfo(
            is_locked=row.is_locked,
            locked_at=row.locked_at,
            lock_reason=row.lock_reason,
            failed_attempts=row.failed_attempts,
            lock_until=row.lock_until,
        ),
        email_verification=EmailVerification(
            is_verified=row.is_email_verified,
            verification_token=row.email_verification_token,
            verified_at=row.email_verified_at,
            expires_at=row.email_verification_expires_at,
        ),
        password_reset_token=password_reset_token,
        two_factor_secret=two_factor_secret,
    )


def _user_to_values(user: User) -> dict[str, _ColumnValue]:
    return {
        'id': user.id.to_raw(),
        'username': user.username.to_raw(),
        'email': user.email.to_raw(),
        'hashed_password': user.hashed_password.to_raw(),
        'deleted_at': user.deleted_at.to_raw(),
        'is_locked': user.account_lock.is_locked,
        'locked_at': user.account_lock.locked_at,
        'lock_reason': user.account_lock.lock_reason,
        'failed_attempts': user.account_lock.failed_attempts,
        'lock_until': user.account_lock.lock_until,
        'is_email_verified': user.email_verification.is_verified,
        'email_verification_token': user.email_verification.verification_token,
        'email_verified_at': user.email_verification.verified_at,
        'email_verification_expires_at': user.email_verification.expires_at,
        'password_reset_token': user.password_reset_token.token if user.password_reset_token else None,
        'password_reset_created_at': user.password_reset_token.created_at if user.password_reset_token else None,
        'password_reset_expires_at': user.password_reset_token.expires_at if user.password_reset_token else None,
        'password_reset_used': user.password_reset_token.is_used if user.password_reset_token else False,
        'two_factor_secret': user.two_factor_secret.secret if user.two_factor_secret else None,
        'two_factor_enabled_at': user.two_factor_secret.enabled_at if user.two_factor_secret else None,
        'two_factor_backup_codes': list(user.two_factor_secret.backup_codes) if user.two_factor_secret else None,
    }


@final
class SQLAlchemyUserRepo(SQLAlchemyRepo, UserRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    @override
    async def acquire_by_id(self, user_id: UserID) -> User | None:
        result = await self._session.execute(
            select(USERS_TABLE).where(USERS_TABLE.c.id == user_id.to_raw())
        )
        row = result.mappings().first()
        return _row_to_user(row) if row else None

    @override
    async def acquire_by_username(self, username: Username) -> User | None:
        result = await self._session.execute(
            select(USERS_TABLE).where(USERS_TABLE.c.username == username.to_raw())
        )
        row = result.mappings().first()
        return _row_to_user(row) if row else None

    @override
    async def acquire_by_email(self, email: Email) -> User | None:
        if email.to_raw() is None:
            return None
        result = await self._session.execute(
            select(USERS_TABLE).where(USERS_TABLE.c.email == email.to_raw())
        )
        row = result.mappings().first()
        return _row_to_user(row) if row else None

    @override
    async def add(self, user: User) -> None:
        _ = await self._session.execute(USERS_TABLE.insert().values(**_user_to_values(user)))
        await self._session.flush()

    @override
    async def update(self, user: User) -> None:
        _ = await self._session.execute(
            USERS_TABLE.update()
            .where(USERS_TABLE.c.id == user.id.to_raw())
            .values(**_user_to_values(user))
        )
        await self._session.flush()

    @override
    async def check_username_exists(self, username: Username) -> bool:
        result = await self._session.scalar(
            select(exists().where(USERS_TABLE.c.username == username.to_raw()))
        )
        return bool(result)

    @override
    async def check_email_exists(self, email: Email) -> bool:
        if email.to_raw() is None:
            return False
        result = await self._session.scalar(
            select(exists().where(USERS_TABLE.c.email == email.to_raw()))
        )
        return bool(result)

    @override
    async def get_all_user_ids(self) -> list[str]:
        result = await self._session.execute(
            select(USER_ID_COLUMN)
        )
        return [str(row) for row in result.scalars().all()]
