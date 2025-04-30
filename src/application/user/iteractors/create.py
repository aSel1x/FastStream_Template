import logging
from dataclasses import dataclass
from uuid import UUID

from domain.user.service import UserService

from application.common.dto import BaseDTO
from application.common.interfaces import InteractorInterface, UnitOfWorkInterface

logger = logging.getLogger(__name__)


@dataclass
class CreateUserInputDTO(BaseDTO):
    username: str
    password: str


class CreateUserInteractor(InteractorInterface[CreateUserInputDTO, UUID]):
    def __init__(self, uow: UnitOfWorkInterface, user_service: UserService) -> None:
        self._uow = uow
        self._user_service = user_service

    async def __call__(self, dto: CreateUserInputDTO) -> UUID:
        await self._user_service.check_username_exists(username=dto.username)

        user = await self._user_service.create(
            username=dto.username,
            password=dto.password,
        )
        await self._uow.commit()

        #  TODO: Event publishing

        logger.info('User created', extra={'user_id': user.uuid, 'user': user})
        return user.uuid
