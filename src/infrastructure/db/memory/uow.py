import logging
from typing import override

from application.common.interfaces.persistence.uow import UnitOfWorkInterface
from domain.common.event import BaseEvent

logger = logging.getLogger(__name__)


class InMemoryUoW(UnitOfWorkInterface):
    def __init__(self) -> None:
        self._pending_events: list[BaseEvent] = []

    @override
    def add_events(self, events: list[BaseEvent]) -> None:
        self._pending_events.extend(events)

    @override
    async def commit(self) -> None:
        logger.debug('Committing in-memory transaction (does nothing).')
        self._pending_events.clear()

    @override
    async def rollback(self) -> None:
        logger.debug('Rolling back in-memory transaction (does nothing).')
        self._pending_events.clear()
