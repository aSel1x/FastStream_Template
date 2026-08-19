from datetime import datetime
from typing import ClassVar, final, override
from uuid import UUID

from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import select
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from domain.audit import AuditLog, AuditRepositoryInterface
from infrastructure.db.sqlalchemy.models.audit import AUDIT_LOGS_TABLE
from infrastructure.db.sqlalchemy.repositories.base import SQLAlchemyRepo


class _AuditLogRow(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    id: UUID
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    details: dict[str, JsonValue] | None
    ip_address: str | None
    user_agent: str | None
    timestamp: datetime
    success: bool


@final
class SQLAlchemyAuditLogRepo(SQLAlchemyRepo, AuditRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    @override
    async def add(self, log: AuditLog) -> None:
        _ = await self._session.execute(
            AUDIT_LOGS_TABLE.insert().values(
                id=log.id,
                user_id=log.user_id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                details=log.details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                timestamp=log.timestamp,
                success=log.success,
            )
        )

    @override
    async def get_by_user_id(self, user_id: UUID, limit: int = 100) -> list[AuditLog]:
        result = await self._session.execute(
            select(AUDIT_LOGS_TABLE)
            .where(AUDIT_LOGS_TABLE.c.user_id == user_id)
            .order_by(AUDIT_LOGS_TABLE.c.timestamp.desc())
            .limit(limit)
        )
        return [_row_to_audit_log(row) for row in result.mappings().all()]

    @override
    async def get_by_entity(self, entity_type: str, entity_id: UUID, limit: int = 100) -> list[AuditLog]:
        result = await self._session.execute(
            select(AUDIT_LOGS_TABLE)
            .where(AUDIT_LOGS_TABLE.c.entity_type == entity_type)
            .where(AUDIT_LOGS_TABLE.c.entity_id == entity_id)
            .order_by(AUDIT_LOGS_TABLE.c.timestamp.desc())
            .limit(limit)
        )
        return [_row_to_audit_log(row) for row in result.mappings().all()]


def _row_to_audit_log(mapping: RowMapping) -> AuditLog:
    row = _AuditLogRow.model_validate(mapping)
    return AuditLog(
        id=row.id,
        user_id=row.user_id,
        action=row.action,
        entity_type=row.entity_type,
        entity_id=row.entity_id,
        details=row.details or {},
        ip_address=row.ip_address,
        user_agent=row.user_agent,
        timestamp=row.timestamp,
        success=row.success,
    )
