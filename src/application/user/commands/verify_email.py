from typing import final
from dataclasses import dataclass
from uuid import UUID

from application.common.interfaces import UnitOfWorkInterface
from application.user.services import UserService
from domain.user.value_objects import UserID


@dataclass
class VerifyEmailInput:
    user_id: str
    token: str


@dataclass
class VerifyEmailOutput:
    success: bool


@final
class VerifyEmailUseCase:
    def __init__(
        self,
        user_service: UserService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._uow = uow

    async def __call__(self, input: VerifyEmailInput) -> VerifyEmailOutput:
        user = await self._user_service.verify_email(
            UserID(UUID(input.user_id)),
            input.token,
        )

        self._uow.add_events(user.pull_events())
        await self._uow.commit()

        return VerifyEmailOutput(success=True)
