from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import final
from uuid import UUID

from infrastructure.db.sqlalchemy.models.outbox import OutboxEvent
from sqlalchemy import delete, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

MAX_ATTEMPTS: int = 8
BACKOFF_CAP_SECONDS: int = 300


def backoff_delay(attempts: int) -> timedelta:
    """Exponential backoff, base 2, capped, so a broken event retries slower and slower.

    `1 << n` rather than `2**n`: the typeshed signature for `int.__pow__` widens to `Any`.
    The base is therefore fixed by the shift and is not configurable; a `BACKOFF_BASE_SECONDS`
    constant used to sit here claiming otherwise, which nothing read.
    """
    seconds: int = min(1 << attempts, BACKOFF_CAP_SECONDS)
    return timedelta(seconds=seconds)


@final
class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: OutboxEvent) -> None:
        self._session.add(event)

    async def get_unprocessed(self, limit: int = 100) -> list[OutboxEvent]:
        """Claim a batch of due events.

        `FOR UPDATE SKIP LOCKED` is what makes several worker replicas safe; the caller owns
        the surrounding transaction and must end it.
        """
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.processed_at.is_(None))
            .where(OutboxEvent.failed_at.is_(None))
            .where(or_(OutboxEvent.next_attempt_at.is_(None), OutboxEvent.next_attempt_at <= now))
            .order_by(OutboxEvent.created_at.asc(), OutboxEvent.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars().all())

    async def mark_processed(self, events: Sequence[OutboxEvent]) -> None:
        """Mark events handled and scrub any credential their payload carried."""
        now = datetime.now(UTC)
        for event in events:
            payload = dict(event.payload)
            for key in event.sensitive_keys or ():
                _ = payload.pop(key, None)
            event.payload = payload
            event.sensitive_keys = None
            event.processed_at = now
            event.last_error = None

    async def reschedule(self, event: OutboxEvent, error: str) -> None:
        """Record a failed attempt and either back off or give up on the event."""
        event.attempts += 1
        event.last_error = error[:2000]
        if event.attempts >= MAX_ATTEMPTS:
            event.failed_at = datetime.now(UTC)
            event.next_attempt_at = None
        else:
            event.next_attempt_at = datetime.now(UTC) + backoff_delay(event.attempts)

    async def list_failed(self, limit: int = 100) -> list[OutboxEvent]:
        result = await self._session.execute(
            select(OutboxEvent)
            .where(OutboxEvent.failed_at.isnot(None))
            .order_by(OutboxEvent.failed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def replay(self, event_ids: list[UUID]) -> int:
        """Put dead-lettered events back in the queue."""
        result = await self._session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.id.in_(event_ids))
            .where(OutboxEvent.failed_at.isnot(None))
            .values(failed_at=None, attempts=0, next_attempt_at=None, last_error=None)
        )
        return result.rowcount if isinstance(result, CursorResult) else 0

    async def delete_processed_older_than(self, before: datetime) -> int:
        result = await self._session.execute(
            delete(OutboxEvent)
            .where(OutboxEvent.processed_at.isnot(None))
            .where(OutboxEvent.processed_at < before)
        )
        return result.rowcount if isinstance(result, CursorResult) else 0
