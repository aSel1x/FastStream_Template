import logging
from uuid import UUID

from domain.user import entities
from domain.user.service import UserService

from application.common.interfaces import InteractorInterface, UnitOfWorkInterface

logger = logging.getLogger(__name__)


class ReadUserInteractor(InteractorInterface[UUID, entities.User]):
    def __init__(self, uow: UnitOfWorkInterface, user_service: UserService) -> None:
        self._uow = uow
        self._user_service = user_service

    async def __call__(self, uuid: UUID) -> entities.User:
        user = await self._user_service.read(uuid)

        #  TODO: Event publishing

        logger.info('User readed', extra={'user_id': user.uuid, 'user': user})
        return user
