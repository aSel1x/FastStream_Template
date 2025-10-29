import logging
from dataclasses import dataclass
from typing import override
from uuid import UUID

from domain.user.service import UserService
from domain.user.value_objects import Email, PlainPassword, Username

from application.common.dto import BaseDTO
from application.common.interfaces import InteractorInterface, UnitOfWorkInterface

logger = logging.getLogger(__name__)


@dataclass
class CreateUserInputDTO(BaseDTO):
    username: str
    password: str
    email: str | None = None


class CreateUserInteractor(InteractorInterface[CreateUserInputDTO, UUID]):
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
    async def __call__(self, dto: CreateUserInputDTO) -> UUID:
        username = Username(dto.username)
        email = Email(dto.email) if dto.email else None
        password = PlainPassword(dto.password)

        user = await self._user_service.create(
            username=username, email=email, password=password
        )
        await self._uow.commit()

        logger.info('User created', extra={'user_id': user.uuid, 'user': user})
        return user.uuid.to_raw()
