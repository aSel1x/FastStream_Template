import logging
from typing import override

from application.common.interfaces import UnitOfWorkInterface
from domain.common.event import BaseEvent
from domain.common.service import BaseService
from infrastructure.mediator import EventBus
from infrastructure.queue import EventPublisher

logger = logging.getLogger(__name__)


class InMemoryUoW(UnitOfWorkInterface):
    _event_bus: EventBus
    _event_publisher: EventPublisher | None

    def __init__(
        self,
        event_bus: EventBus,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._event_publisher = event_publisher

    @override
    async def commit(self) -> None:
        logger.debug('Committing in-memory transaction (does nothing).')

        events: list[BaseEvent] = BaseService.collect_all_events()

        if events:
            await self._event_bus.publish_many(events)
            logger.debug(f'Published {len(events)} domain events to EventBus')

            if self._event_publisher:
                await self._event_publisher.publish_many(events)
                logger.debug(f'Published {len(events)} domain events to RabbitMQ')

    @override
    async def rollback(self) -> None:
        logger.debug('Rolling back in-memory transaction (does nothing).')

        BaseService.clear_all_events()
