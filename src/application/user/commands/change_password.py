from typing import final
from dataclasses import dataclass
from uuid import UUID

from application.common.interfaces import UnitOfWorkInterface
from application.user.services import UserService
from domain.user.value_objects import PlainPassword, UserID


@dataclass
class ChangePasswordInput:
    user_id: UUID
    old_password: str
    new_password: str


@dataclass
class ChangePasswordOutput:
    success: bool


@final
class ChangePasswordUseCase:
    def __init__(
        self,
        user_service: UserService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._uow = uow

    async def __call__(self, input: ChangePasswordInput) -> ChangePasswordOutput:
        user = await self._user_service.get_user_by_id(UserID(input.user_id))
        updated_user = await self._user_service.change_password(
            user,
            PlainPassword(input.old_password),
            PlainPassword(input.new_password),
        )

        self._uow.add_events(updated_user.pull_events())
        await self._uow.commit()

        return ChangePasswordOutput(success=True)
