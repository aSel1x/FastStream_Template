from dataclasses import dataclass
from typing import final

from application.common.interfaces import UnitOfWorkInterface
from application.user.services import UserService


@dataclass
class VerifyEmailInput:
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

    async def __call__(self, data: VerifyEmailInput) -> VerifyEmailOutput:
        _ = await self._user_service.verify_email(data.token)

        await self._uow.commit()

        return VerifyEmailOutput(success=True)
