from typing import final
from uuid import UUID

from application.common.interfaces import UnitOfWorkInterface
from application.user.services import UserService
from domain.user.value_objects import UserID


@final
class DeleteMeUseCase:
    def __init__(
        self,
        user_service: UserService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._uow = uow

    async def __call__(self, user_id: UUID) -> None:
        user = await self._user_service.delete_user(UserID(user_id))
        self._uow.add_events(user.pull_events())
        await self._uow.commit()
