import logging
from dataclasses import dataclass
from typing import override
from uuid import UUID

from domain.common.entity import EntityUUID
from domain.user.service import UserService
from domain.user.value_objects import Email, Username

from application.common.dto import BaseDTO
from application.common.interfaces import InteractorInterface, UnitOfWorkInterface

logger = logging.getLogger(__name__)


@dataclass
class UpdateProfileInputDTO(BaseDTO):
    username: str | None = None
    email: str | None = None


@dataclass
class UpdateProfileOutputDTO(BaseDTO):
    user_id: str
    username: str
    created_at: str
    updated_at: str
    email: str | None = None


class UpdateProfileInteractor(
    InteractorInterface[tuple[UUID, UpdateProfileInputDTO], UpdateProfileOutputDTO]
):
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
    async def __call__(
        self, input_data: tuple[UUID, UpdateProfileInputDTO]
    ) -> UpdateProfileOutputDTO:
        user_id, dto = input_data

        entity_uuid = EntityUUID(user_id)
        user = await self._user_service.get_user_by_uuid(entity_uuid)

        new_username = Username(dto.username) if dto.username else None
        new_email = Email(dto.email) if dto.email else None

        updated_user = await self._user_service.update_user(
            user,
            username=new_username,
            email=new_email,
        )

        await self._uow.commit()

        logger.info(f'Updated user {updated_user.uuid} profile')

        return UpdateProfileOutputDTO(
            user_id=str(updated_user.uuid.to_raw()),
            username=updated_user.username.to_raw() or '',
            email=updated_user.email.to_raw(),
            created_at=updated_user.created_at.to_raw().isoformat(),
            updated_at=updated_user.updated_at.to_raw().isoformat(),
        )
