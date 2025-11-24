import logging
from dataclasses import dataclass
from typing import override
from uuid import UUID

from domain.user.service import UserService
from domain.user.value_objects import Email, UserID, Username

from application.common.dto import BaseDTO
from application.common.interfaces import (
    EventPublisherInterface,
    InteractorInterface,
    UnitOfWorkInterface,
)

logger = logging.getLogger(__name__)


@dataclass
class UpdateProfileInputDTO(BaseDTO):
    user_id: UUID
    username: str | None = None
    email: str | None = None


@dataclass
class UpdateProfileOutputDTO(BaseDTO):
    username: str
    email: str | None = None


class UpdateProfileInteractor(
    InteractorInterface[UpdateProfileInputDTO, UpdateProfileOutputDTO]
):
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
    async def __call__(self, dto: UpdateProfileInputDTO) -> UpdateProfileOutputDTO:
        user_id_vo = UserID(dto.user_id)
        user = await self._user_service.get_user_by_id(user_id_vo)

        new_username = Username(dto.username) if dto.username else None
        new_email = Email(dto.email) if dto.email else None

        updated_user = await self._user_service.update_user(
            user,
            username=new_username,
            email=new_email,
        )

        await self._uow.commit()

        logger.info(f'Updated user {updated_user.id.to_raw()} profile')

        await self._event_publisher.publish(self._user_service.pull_events())

        return UpdateProfileOutputDTO(
            username=updated_user.username.to_raw() or '',
            email=updated_user.email.to_raw(),
        )
