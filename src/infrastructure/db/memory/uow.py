import logging
from collections.abc import Sequence
from types import TracebackType
from typing import Self, override

from application.common.interfaces.persistence.uow import UnitOfWorkInterface
from domain.common.event import BaseEvent
from domain.common.event_dispatcher import DomainEventDispatcher

logger = logging.getLogger(__name__)


class InMemoryUoW(UnitOfWorkInterface):
    """A UoW with no database behind it, for tests and in-memory wiring.

    It keeps committed events instead of discarding them: silently dropping every event made
    it impossible for a test on this UoW to notice that events were never emitted at all.
    """

    def __init__(self) -> None:
        self._pending_events: list[BaseEvent] = []
        self._aggregates: list[DomainEventDispatcher] = []
        self.committed_events: list[BaseEvent] = []

    @override
    def register(self, aggregate: DomainEventDispatcher) -> None:
        if aggregate not in self._aggregates:
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
        logger.debug('Committing in-memory transaction (persists nothing).')
        self.committed_events.extend(self._drain())

    @override
    async def rollback(self) -> None:
        logger.debug('Rolling back in-memory transaction (persists nothing).')
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
