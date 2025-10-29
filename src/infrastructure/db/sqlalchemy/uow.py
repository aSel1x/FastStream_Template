from typing import override

from application.common.interfaces.uow import UnitOfWorkInterface
from domain.common.event import BaseEvent
from domain.common.service import BaseService
from infrastructure.mediator import EventBus
from infrastructure.queue import EventPublisher

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyUoW(UnitOfWorkInterface):
    _session: AsyncSession
    _event_bus: EventBus
    _event_publisher: EventPublisher | None

    def __init__(
        self,
        session: AsyncSession,
        event_bus: EventBus,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self._session = session
        self._event_bus = event_bus
        self._event_publisher = event_publisher

    @override
    async def commit(self) -> None:
        try:
            await self._session.commit()

            events: list[BaseEvent] = BaseService.collect_all_events()

            if events:
                await self._event_bus.publish_many(events)

                if self._event_publisher:
                    await self._event_publisher.publish_many(events)
        except SQLAlchemyError:
            raise

    @override
    async def rollback(self) -> None:
        try:
            await self._session.rollback()

            BaseService.clear_all_events()
        except SQLAlchemyError:
            raise
