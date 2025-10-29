import logging
from typing import override
from uuid import UUID

from domain.common.entity import EntityUUID
from domain.user import entities
from domain.user.service import UserService

from application.common.interfaces import InteractorInterface, UnitOfWorkInterface

logger = logging.getLogger(__name__)


class ReadUserInteractor(InteractorInterface[UUID, entities.User]):
    def __init__(self, uow: UnitOfWorkInterface, user_service: UserService) -> None:
        self._uow: UnitOfWorkInterface = uow
        self._user_service: UserService = user_service

    @override
    async def __call__(self, uuid: UUID) -> entities.User:
        entity_uuid = EntityUUID(uuid)
        user = await self._user_service.get_user_by_uuid(entity_uuid)
        await self._uow.commit()

        logger.info('User read', extra={'user_id': user.uuid, 'user': user})
        return user
