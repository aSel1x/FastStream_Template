from datetime import datetime
from typing import ClassVar, final, override
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from domain.user.entities.session import DeviceInfo, RefreshToken, SessionAggregate
from domain.user.interfaces import SessionRepositoryInterface
from domain.user.value_objects import TokenHash, UserID
from infrastructure.db.sqlalchemy.models.session import REFRESH_TOKENS_TABLE, SESSIONS_TABLE
from infrastructure.db.sqlalchemy.repositories.base import SQLAlchemyRepo
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession


class _SessionRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    session_id: UUID
    user_id: UUID
    user_agent: str | None
    ip_address: str | None
    device_name: str | None
    browser: str | None
    os: str | None
    is_mobile: bool
    created_at: datetime
    expires_at: datetime
    is_revoked: bool


class _RefreshTokenRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: UUID
    session_id: UUID
    token_hash: bytes
    expires_at: datetime
    is_revoked: bool
    created_at: datetime


def _device_info_from_row(row: _SessionRow) -> DeviceInfo:
    return DeviceInfo(
        user_agent=row.user_agent,
        ip_address=row.ip_address,
        device_name=row.device_name,
        browser=row.browser,
        os=row.os,
        is_mobile=row.is_mobile,
    )


def _session_from_rows(
    row: _SessionRow, refresh_tokens: tuple[RefreshToken, ...]
) -> SessionAggregate:
    return SessionAggregate(
        session_id=row.session_id,
        user_id=UserID(row.user_id),
        device_info=_device_info_from_row(row),
        created_at=row.created_at,
        expires_at=row.expires_at,
        is_revoked=row.is_revoked,
        refresh_tokens=refresh_tokens,
    )


def _refresh_token_from_row(row: _RefreshTokenRow) -> RefreshToken:
    return RefreshToken(
        id=row.id,
        token_hash=TokenHash(row.token_hash),
        expires_at=row.expires_at,
        is_revoked=row.is_revoked,
        created_at=row.created_at,
    )


@final
class SQLAlchemySessionRepo(SQLAlchemyRepo, SessionRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    @override
    async def acquire_by_session_id(self, session_id: UUID) -> SessionAggregate | None:
        result = await self._session.execute(
            select(SESSIONS_TABLE).where(SESSIONS_TABLE.c.session_id == session_id)
        )
        mapping = result.mappings().first()
        if not mapping:
            return None
        row = _SessionRow.model_validate(mapping)

        tokens = await self._session.execute(
            select(REFRESH_TOKENS_TABLE).where(REFRESH_TOKENS_TABLE.c.session_id == session_id)
        )
        refresh_tokens = tuple(
            _refresh_token_from_row(_RefreshTokenRow.model_validate(token_mapping))
            for token_mapping in tokens.mappings().all()
        )

        return _session_from_rows(row, refresh_tokens)

    @override
    async def acquire_by_user_id(self, user_id: UserID) -> list[SessionAggregate]:
        result = await self._session.execute(
            select(SESSIONS_TABLE).where(
                and_(
                    SESSIONS_TABLE.c.user_id == user_id.to_raw(),
                    SESSIONS_TABLE.c.is_revoked.is_(False),
                )
            )
        )
        rows = [_SessionRow.model_validate(mapping) for mapping in result.mappings().all()]
        if not rows:
            return []

        # Load the tokens too. Building these aggregates with an empty token tuple meant
        # `session.revoke()` mapped over nothing, and revoking every session left every
        # refresh_tokens row un-revoked in the database.
        tokens_by_session = await self._refresh_tokens_for(
            [row.session_id for row in rows],
        )
        return [_session_from_rows(row, tokens_by_session.get(row.session_id, ())) for row in rows]

    async def _refresh_tokens_for(
        self, session_ids: list[UUID]
    ) -> dict[UUID, tuple[RefreshToken, ...]]:
        """One query for the whole batch, grouped in Python — not one query per session."""
        result = await self._session.execute(
            select(REFRESH_TOKENS_TABLE).where(REFRESH_TOKENS_TABLE.c.session_id.in_(session_ids))
        )
        grouped: dict[UUID, list[RefreshToken]] = {}
        for mapping in result.mappings().all():
            row = _RefreshTokenRow.model_validate(mapping)
            grouped.setdefault(row.session_id, []).append(_refresh_token_from_row(row))
        return {session_id: tuple(tokens) for session_id, tokens in grouped.items()}

    @override
    async def add(self, session: SessionAggregate) -> None:
        _ = await self._session.execute(
            SESSIONS_TABLE.insert().values(
                session_id=session.session_id,
                user_id=session.user_id.to_raw(),
                user_agent=session.device_info.user_agent,
                ip_address=session.device_info.ip_address,
                device_name=session.device_info.device_name,
                browser=session.device_info.browser,
                os=session.device_info.os,
                is_mobile=session.device_info.is_mobile,
                created_at=session.created_at,
                expires_at=session.expires_at,
                is_revoked=session.is_revoked,
            )
        )

        for token in session.refresh_tokens:
            _ = await self._session.execute(
                REFRESH_TOKENS_TABLE.insert().values(
                    id=token.id,
                    session_id=session.session_id,
                    token_hash=token.token_hash.to_raw(),
                    expires_at=token.expires_at,
                    is_revoked=token.is_revoked,
                    created_at=token.created_at,
                )
            )

        await self._session.flush()

    @override
    async def update(self, session: SessionAggregate) -> None:
        _ = await self._session.execute(
            SESSIONS_TABLE.update()
            .where(SESSIONS_TABLE.c.session_id == session.session_id)
            .values(
                is_revoked=session.is_revoked,
                expires_at=session.expires_at,
            )
        )

        # Upsert, not update: refresh-token rotation adds a token on every refresh, and an
        # UPDATE-only path silently dropped it — the caller got a token the database had
        # never heard of.
        for token in session.refresh_tokens:
            statement = (
                insert(REFRESH_TOKENS_TABLE)
                .values(
                    id=token.id,
                    session_id=session.session_id,
                    token_hash=token.token_hash.to_raw(),
                    expires_at=token.expires_at,
                    is_revoked=token.is_revoked,
                    created_at=token.created_at,
                )
                .on_conflict_do_update(
                    index_elements=[REFRESH_TOKENS_TABLE.c.id],
                    set_={'is_revoked': token.is_revoked, 'expires_at': token.expires_at},
                )
            )
            _ = await self._session.execute(statement)
        await self._session.flush()

    @override
    async def delete(self, session_id: UUID) -> None:
        _ = await self._session.execute(
            SESSIONS_TABLE.delete().where(SESSIONS_TABLE.c.session_id == session_id)
        )
        _ = await self._session.execute(
            REFRESH_TOKENS_TABLE.delete().where(REFRESH_TOKENS_TABLE.c.session_id == session_id)
        )
        await self._session.flush()

    @override
    async def delete_by_user_id(self, user_id: UserID) -> None:
        # refresh_tokens.session_id cascades, so deleting the sessions removes the tokens.
        _ = await self._session.execute(
            SESSIONS_TABLE.delete().where(SESSIONS_TABLE.c.user_id == user_id.to_raw())
        )
        await self._session.flush()

    @override
    async def delete_expired(self, before: datetime) -> int:
        """Drop sessions that expired before `before`. Nothing else ever removes them."""
        result = await self._session.execute(
            SESSIONS_TABLE.delete().where(SESSIONS_TABLE.c.expires_at < before)
        )
        await self._session.flush()
        return result.rowcount if isinstance(result, CursorResult) else 0

    @override
    async def acquire_by_token_hash(self, token_hash: bytes) -> SessionAggregate | None:
        token_result = await self._session.execute(
            select(REFRESH_TOKENS_TABLE)
            .where(REFRESH_TOKENS_TABLE.c.token_hash == token_hash)
            .where(REFRESH_TOKENS_TABLE.c.is_revoked.is_(False))
        )
        token_mapping = token_result.mappings().first()

        if not token_mapping:
            return None
        token_row = _RefreshTokenRow.model_validate(token_mapping)

        session_result = await self._session.execute(
            select(SESSIONS_TABLE).where(SESSIONS_TABLE.c.session_id == token_row.session_id)
        )
        session_mapping = session_result.mappings().first()

        if not session_mapping:
            return None
        session_row = _SessionRow.model_validate(session_mapping)
        if session_row.is_revoked:
            return None

        all_tokens = await self._session.execute(
            select(REFRESH_TOKENS_TABLE).where(
                REFRESH_TOKENS_TABLE.c.session_id == token_row.session_id
            )
        )

        refresh_tokens = tuple(
            _refresh_token_from_row(_RefreshTokenRow.model_validate(t))
            for t in all_tokens.mappings().all()
        )

        return _session_from_rows(session_row, refresh_tokens)
