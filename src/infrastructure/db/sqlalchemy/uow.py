from collections.abc import Sequence
from datetime import UTC, datetime
from types import TracebackType
from typing import Self, final, override
from uuid import uuid4

from application.common.interfaces.persistence.uow import EventHandler, UnitOfWorkInterface
from domain.common.event import BaseEvent
from domain.common.event_dispatcher import DomainEventDispatcher
from domain.user.events import event_aggregate
from infrastructure.db.sqlalchemy.models.outbox import OutboxEvent
from sqlalchemy.ext.asyncio import AsyncSession


@final
class SQLAlchemyUoW(UnitOfWorkInterface):
    _session: AsyncSession

    def __init__(
        self, session: AsyncSession, event_handlers: list[EventHandler] | None = None
    ) -> None:
        self._session = session
        self._pending_events: list[BaseEvent] = []
        self._aggregates: list[DomainEventDispatcher] = []
        self._event_handlers = event_handlers or []

    @override
    def register(self, aggregate: DomainEventDispatcher) -> None:
        # Identity, not equality: two aggregates with the same id but different unpulled
        # events are two different things to drain.
        if not any(tracked is aggregate for tracked in self._aggregates):
            self._aggregates.append(aggregate)

    @override
    def add_events(self, events: Sequence[BaseEvent]) -> None:
        self._pending_events.extend(events)

    def _drain(self) -> list[BaseEvent]:
        for aggregate in self._aggregates:
            self._pending_events.extend(aggregate.pull_events())
        self._aggregates.clear()
        drained = self._pending_events[:]
        self._pending_events.clear()
        return drained

    @override
    async def commit(self) -> None:
        events = self._drain()
        try:
            for event in events:
                self._persist_outbox_event(event)

            # Handlers run before the commit on purpose: whatever they write (the audit log,
            # today) lands in the same transaction as the change that produced the event.
            for event in events:
                for handler in self._event_handlers:
                    await handler(event)

            await self._session.commit()
        except Exception:
            # Not just SQLAlchemyError: a handler raising anything else would otherwise leave
            # the session open with the change half-applied.
            await self._session.rollback()
            raise

    @override
    async def rollback(self) -> None:
        try:
            await self._session.rollback()
        finally:
            _ = self._drain()

    @override
    async def __aenter__(self) -> Self:
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc is None:
            await self.commit()
        else:
            await self.rollback()

    def _persist_outbox_event(self, event: BaseEvent) -> None:
        aggregate_type, aggregate_id = event_aggregate(event)

        sensitive = sorted(type(event).sensitive_fields)
        outbox_event = OutboxEvent(
            id=uuid4(),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=type(event).wire_name(),
            payload=event.to_payload(),
            sensitive_keys=sensitive or None,
            created_at=datetime.now(UTC),
            processed_at=None,
        )
        self._session.add(outbox_event)
