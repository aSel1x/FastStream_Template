import logging
from typing import override
from uuid import UUID

from domain.user.service import UserService
from domain.user.value_objects import UserID

from application.common.interfaces import (
    EventPublisherInterface,
    InteractorInterface,
    UnitOfWorkInterface,
)

logger = logging.getLogger(__name__)


class DeleteMeInteractor(InteractorInterface[UUID, None]):
    def __init__(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
        event_publisher: EventPublisherInterface,
    ) -> None:
        self._uow: UnitOfWorkInterface = uow
        self._user_service: UserService = user_service
        self._event_publisher: EventPublisherInterface = event_publisher

    @override
    async def __call__(self, user_id: UUID) -> None:
        user_id_vo = UserID(user_id)
        await self._user_service.delete_user(user_id_vo)
        await self._uow.commit()

        logger.info('User deleted', extra={'user_id': user_id_vo.to_raw()})

        await self._event_publisher.publish(self._user_service.pull_events())

        return None
