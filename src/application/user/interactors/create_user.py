import logging
from dataclasses import dataclass
from typing import override
from uuid import UUID

from domain.user.service import UserService
from domain.user.value_objects import Email, PlainPassword, UserID, Username

from application.common.dto import BaseDTO
from application.common.interfaces import (
    EventPublisherInterface,
    InteractorInterface,
    UnitOfWorkInterface,
    UUIDGeneratorInterface,
)

logger = logging.getLogger(__name__)


@dataclass
class CreateUserInputDTO(BaseDTO):
    username: str
    password: str
    email: str | None = None


class CreateUserInteractor(InteractorInterface[CreateUserInputDTO, UUID]):
    def __init__(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
        uuid_generator: UUIDGeneratorInterface,
        event_publisher: EventPublisherInterface,
    ) -> None:
        self._uow: UnitOfWorkInterface = uow
        self._user_service: UserService = user_service
        self._uuid_generator: UUIDGeneratorInterface = uuid_generator
        self._event_publisher: EventPublisherInterface = event_publisher

    @override
    async def __call__(self, dto: CreateUserInputDTO) -> UUID:
        username = Username(dto.username)
        email = Email(dto.email) if dto.email else None
        password = PlainPassword(dto.password)
        user_id = UserID(self._uuid_generator())

        user = await self._user_service.create(
            user_id=user_id,
            username=username,
            email=email,
            password=password,
        )
        await self._uow.commit()

        logger.info('User created', extra={'user_id': user.id.to_raw(), 'user': user})

        await self._event_publisher.publish(self._user_service.pull_events())

        return user.id.to_raw()
