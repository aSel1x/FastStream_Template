import logging
from dataclasses import dataclass
from typing import override
from uuid import UUID

from domain.user.service import UserService
from domain.user.value_objects import UserID

from application.common.dto import BaseDTO
from application.common.interfaces import (
    EventPublisherInterface,
    InteractorInterface,
    UnitOfWorkInterface,
)

logger = logging.getLogger(__name__)


@dataclass
class GetMeOutputDTO(BaseDTO):
    user_id: str
    username: str
    email: str | None = None


class GetMeInteractor(InteractorInterface[UUID, GetMeOutputDTO]):
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
    async def __call__(self, user_id: UUID) -> GetMeOutputDTO:
        user_id_vo = UserID(user_id)
        user = await self._user_service.get_user_by_id(user_id_vo)

        await self._uow.commit()

        logger.info(f'Retrieved user {user.id.to_raw()} profile')

        await self._event_publisher.publish(self._user_service.pull_events())

        return GetMeOutputDTO(
            user_id=str(user.id.to_raw()),
            username=user.username.to_raw() or '',
            email=user.email.to_raw(),
        )
