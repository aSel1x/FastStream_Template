from datetime import UTC, datetime
from typing import final
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.sqlalchemy.models.outbox import OutboxEvent


@final
class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: OutboxEvent) -> None:
        self._session.add(event)

    async def get_unprocessed(self, limit: int = 100) -> list[OutboxEvent]:
        result = await self._session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.processed_at.is_(None))
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def mark_processed(self, event_ids: list[UUID]) -> None:
        _ = await self._session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id.in_(event_ids))
            .values(processed_at=datetime.now(UTC))
        )
        await self._session.commit()

    async def delete_processed_older_than(self, before: datetime) -> int:
        result = await self._session.execute(
            delete(OutboxEvent)
            .where(OutboxEvent.processed_at.isnot(None))
            .where(OutboxEvent.processed_at < before)
        )
        if isinstance(result, CursorResult):
            return result.rowcount
        return 0