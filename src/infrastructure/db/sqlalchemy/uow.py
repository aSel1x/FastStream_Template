from datetime import UTC, datetime
from typing import final, override
from uuid import uuid4

from application.common.interfaces.persistence.uow import EventHandler, UnitOfWorkInterface
from domain.common.event import BaseEvent
from domain.user.events import event_aggregate

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.sqlalchemy.models.outbox import OutboxEvent


@final
class SQLAlchemyUoW(UnitOfWorkInterface):
    _session: AsyncSession

    def __init__(self, session: AsyncSession, event_handlers: list[EventHandler] | None = None) -> None:
        self._session = session
        self._pending_events: list[BaseEvent] = []
        self._event_handlers = event_handlers or []

    @override
    def add_events(self, events: list[BaseEvent]) -> None:
        self._pending_events.extend(events)

    @override
    async def commit(self) -> None:
        try:
            for event in self._pending_events:
                self._persist_outbox_event(event)

            for event in self._pending_events:
                for handler in self._event_handlers:
                    await handler(event)

            await self._session.commit()
            self._pending_events.clear()
        except SQLAlchemyError:
            await self._session.rollback()
            self._pending_events.clear()
            raise

    @override
    async def rollback(self) -> None:
        try:
            await self._session.rollback()
        except SQLAlchemyError:
            raise
        finally:
            self._pending_events.clear()

    def _persist_outbox_event(self, event: BaseEvent) -> None:
        aggregate_type, aggregate_id = event_aggregate(event)

        outbox_event = OutboxEvent(
            id=uuid4(),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event.__class__.__name__,
            payload=event.to_payload(),
            created_at=datetime.now(UTC),
            processed_at=None,
        )
        self._session.add(outbox_event)
