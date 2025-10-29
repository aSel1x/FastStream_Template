import logging
from dataclasses import dataclass
from typing import override
from uuid import UUID

from domain.common.entity import EntityUUID
from domain.user.service import UserService

from application.common.dto import BaseDTO
from application.common.interfaces import InteractorInterface, UnitOfWorkInterface

logger = logging.getLogger(__name__)


@dataclass
class GetMeOutputDTO(BaseDTO):
    user_id: str
    username: str
    created_at: str
    updated_at: str
    email: str | None = None


class GetMeInteractor(InteractorInterface[UUID, GetMeOutputDTO]):
    def __init__(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
    ) -> None:
        self._uow: UnitOfWorkInterface = uow
        self._user_service: UserService = user_service

    @override
    async def __call__(self, user_id: UUID) -> GetMeOutputDTO:
        entity_uuid = EntityUUID(user_id)
        user = await self._user_service.get_user_by_uuid(entity_uuid)

        await self._uow.commit()

        logger.info(f'Retrieved user {user.uuid} profile')

        return GetMeOutputDTO(
            user_id=str(user.uuid.to_raw()),
            username=user.username.to_raw() or '',
            email=user.email.to_raw(),
            created_at=user.created_at.to_raw().isoformat(),
            updated_at=user.updated_at.to_raw().isoformat(),
        )
