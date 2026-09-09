from datetime import datetime
from typing import ClassVar, final, override
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from domain.common.exceptions import BaseDomainError
from domain.user.entities.user import User
from domain.user.exceptions import (
    ConcurrentModificationError,
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
)
from domain.user.interfaces import UserRepositoryInterface
from domain.user.interfaces.acl.secret_cipher import SecretCipherInterface
from domain.user.value_objects import (
    AccountLockInfo,
    DeletionTime,
    Email,
    EmailVerification,
    HashedPassword,
    PasswordResetToken,
    TokenHash,
    TwoFactorSecret,
    UserID,
    Username,
)
from infrastructure.db.sqlalchemy.models.user import USER_ID_COLUMN, USERS_TABLE
from infrastructure.db.sqlalchemy.repositories.base import SQLAlchemyRepo
from sqlalchemy.engine import CursorResult, RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import exists, select


class _UserRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: UUID
    version: int
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
    email_verification_token_hash: bytes | None
    email_verified_at: datetime | None
    email_verification_expires_at: datetime | None
    password_reset_token_hash: bytes | None
    password_reset_created_at: datetime | None
    password_reset_expires_at: datetime | None
    password_reset_used: bool
    two_factor_secret: bytes | None
    two_factor_enabled_at: datetime | None
    two_factor_backup_codes: list[str] | None


_ColumnValue = UUID | str | bytes | bool | int | datetime | list[str] | None


def _row_to_user(mapping: RowMapping, cipher: SecretCipherInterface) -> User:
    row = _UserRow.model_validate(mapping)

    password_reset_token: PasswordResetToken | None = None
    if row.password_reset_token_hash:
        password_reset_token = PasswordResetToken(
            token_hash=TokenHash(row.password_reset_token_hash),
            created_at=row.password_reset_created_at,
            expires_at=row.password_reset_expires_at,
            is_used=row.password_reset_used,
        )

    two_factor_secret: TwoFactorSecret | None = None
    if row.two_factor_secret:
        two_factor_secret = TwoFactorSecret(
            secret=cipher.decrypt(row.two_factor_secret),
            backup_code_hashes=tuple(
                TokenHash(bytes.fromhex(code)) for code in row.two_factor_backup_codes or ()
            ),
            enabled_at=row.two_factor_enabled_at,
        )

    return User(
        id=UserID(row.id),
        version=row.version,
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
            token_hash=(
                TokenHash(row.email_verification_token_hash)
                if row.email_verification_token_hash
                else None
            ),
            verified_at=row.email_verified_at,
            expires_at=row.email_verification_expires_at,
        ),
        password_reset_token=password_reset_token,
        two_factor_secret=two_factor_secret,
    )


def _user_to_values(user: User, cipher: SecretCipherInterface) -> dict[str, _ColumnValue]:
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
        'email_verification_token_hash': (
            user.email_verification.token_hash.to_raw()
            if user.email_verification.token_hash
            else None
        ),
        'email_verified_at': user.email_verification.verified_at,
        'email_verification_expires_at': user.email_verification.expires_at,
        'password_reset_token_hash': user.password_reset_token.token_hash.to_raw()
        if user.password_reset_token
        else None,
        'password_reset_created_at': user.password_reset_token.created_at
        if user.password_reset_token
        else None,
        'password_reset_expires_at': user.password_reset_token.expires_at
        if user.password_reset_token
        else None,
        'password_reset_used': user.password_reset_token.is_used
        if user.password_reset_token
        else False,
        'two_factor_secret': cipher.encrypt(user.two_factor_secret.secret)
        if user.two_factor_secret
        else None,
        'two_factor_enabled_at': user.two_factor_secret.enabled_at
        if user.two_factor_secret
        else None,
        'two_factor_backup_codes': [
            held.to_raw().hex() for held in user.two_factor_secret.backup_code_hashes
        ]
        if user.two_factor_secret
        else None,
    }


def _uniqueness_error(exc: IntegrityError, user: User) -> BaseDomainError:
    constraint = str(getattr(exc.orig, 'constraint_name', '') or exc.orig or '')
    if 'email' in constraint:
        return EmailAlreadyExistsError(user.email.to_raw())
    if 'username' in constraint:
        return UsernameAlreadyExistsError(user.username.to_raw())
    return UsernameAlreadyExistsError(user.username.to_raw())


@final
class SQLAlchemyUserRepo(SQLAlchemyRepo, UserRepositoryInterface):
    def __init__(self, session: AsyncSession, cipher: SecretCipherInterface) -> None:
        super().__init__(session)
        self._cipher: SecretCipherInterface = cipher

    @override
    async def acquire_by_id(self, user_id: UserID) -> User | None:
        result = await self._session.execute(
            select(USERS_TABLE).where(USERS_TABLE.c.id == user_id.to_raw())
        )
        row = result.mappings().first()
        return _row_to_user(row, self._cipher) if row else None

    @override
    async def acquire_by_username(self, username: Username) -> User | None:
        result = await self._session.execute(
            select(USERS_TABLE).where(
                USERS_TABLE.c.username == username.to_raw(),
                USERS_TABLE.c.deleted_at.is_(None),
            )
        )
        row = result.mappings().first()
        return _row_to_user(row, self._cipher) if row else None

    @override
    async def acquire_by_email(self, email: Email) -> User | None:
        if email.to_raw() is None:
            return None
        result = await self._session.execute(
            select(USERS_TABLE).where(
                USERS_TABLE.c.email == email.to_raw(),
                USERS_TABLE.c.deleted_at.is_(None),
            )
        )
        row = result.mappings().first()
        return _row_to_user(row, self._cipher) if row else None

    @override
    async def acquire_by_verification_token(self, token_hash: TokenHash) -> User | None:
        result = await self._session.execute(
            select(USERS_TABLE).where(
                USERS_TABLE.c.email_verification_token_hash == token_hash.to_raw()
            )
        )
        row = result.mappings().first()
        return _row_to_user(row, self._cipher) if row else None

    @override
    async def acquire_by_reset_token(self, token_hash: TokenHash) -> User | None:
        result = await self._session.execute(
            select(USERS_TABLE).where(
                USERS_TABLE.c.password_reset_token_hash == token_hash.to_raw()
            )
        )
        row = result.mappings().first()
        return _row_to_user(row, self._cipher) if row else None

    @override
    async def add(self, user: User) -> None:
        try:
            _ = await self._session.execute(
                USERS_TABLE.insert().values(**_user_to_values(user, self._cipher))
            )
            await self._session.flush()
        except IntegrityError as exc:
            # The application pre-checks uniqueness, but two concurrent registrations pass
            # that check together. Without this the loser gets a 500 instead of a 409.
            raise _uniqueness_error(exc, user) from exc

    @override
    async def update(self, user: User) -> None:
        values = _user_to_values(user, self._cipher)
        values['version'] = user.version + 1
        try:
            result = await self._session.execute(
                USERS_TABLE.update()
                .where(
                    USERS_TABLE.c.id == user.id.to_raw(),
                    USERS_TABLE.c.version == user.version,
                )
                .values(**values)
            )
            await self._session.flush()
        except IntegrityError as exc:
            raise _uniqueness_error(exc, user) from exc

        # Zero rows means someone else wrote first. Overwriting blindly is how a lockout
        # counter loses increments and a 2FA backup code gets spent twice.
        if isinstance(result, CursorResult) and result.rowcount == 0:
            raise ConcurrentModificationError(str(user.id.to_raw()))

        # Keep the in-memory aggregate in step with the row, so a second update inside the
        # same transaction does not fail its own version check.
        object.__setattr__(user, 'version', user.version + 1)

    @override
    async def check_username_exists(self, username: Username) -> bool:
        result = await self._session.scalar(
            select(
                exists().where(
                    USERS_TABLE.c.username == username.to_raw(),
                    USERS_TABLE.c.deleted_at.is_(None),
                )
            )
        )
        return bool(result)

    @override
    async def check_email_exists(self, email: Email) -> bool:
        if email.to_raw() is None:
            return False
        result = await self._session.scalar(
            select(
                exists().where(
                    USERS_TABLE.c.email == email.to_raw(),
                    USERS_TABLE.c.deleted_at.is_(None),
                )
            )
        )
        return bool(result)

    @override
    async def get_all_user_ids(self) -> list[str]:
        result = await self._session.execute(select(USER_ID_COLUMN))
        return [str(row) for row in result.scalars().all()]
