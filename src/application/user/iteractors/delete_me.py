import logging
from typing import override
from uuid import UUID

from domain.common.entity import EntityUUID
from domain.user.service import UserService

from application.common.interfaces import InteractorInterface, UnitOfWorkInterface

logger = logging.getLogger(__name__)


class DeleteMeInteractor(InteractorInterface[UUID, None]):
    _uow: UnitOfWorkInterface
    _user_service: UserService

    def __init__(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
    ) -> None:
        self._uow = uow
        self._user_service = user_service

    @override
    async def __call__(self, user_id: UUID) -> None:
        entity_uuid = EntityUUID(user_id)

        await self._user_service.delete_user(entity_uuid)
        await self._uow.commit()

        logger.info('User deleted', extra={'user_id': user_id})
