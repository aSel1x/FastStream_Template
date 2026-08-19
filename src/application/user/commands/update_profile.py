from typing import final
from dataclasses import dataclass
from uuid import UUID

from application.common.interfaces import UnitOfWorkInterface
from application.user.services import UserService
from domain.user.value_objects import Email, UserID, Username


@dataclass
class UpdateProfileInput:
    user_id: UUID
    username: str | None = None
    email: str | None = None


@dataclass
class UpdateProfileOutput:
    username: str
    is_email_verified: bool
    is_locked: bool
    has_two_factor: bool
    email: str | None = None


@final
class UpdateProfileUseCase:
    def __init__(
        self,
        user_service: UserService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._uow = uow

    async def __call__(self, input: UpdateProfileInput) -> UpdateProfileOutput:
        user = await self._user_service.get_user_by_id(UserID(input.user_id))
        updated = await self._user_service.update_user(
            user,
            username=Username(input.username) if input.username else None,
            email=Email(input.email) if input.email else None,
        )
        self._uow.add_events(updated.pull_events())
        await self._uow.commit()
        return UpdateProfileOutput(
            username=updated.username.to_raw() or '',
            email=updated.email.to_raw(),
            is_email_verified=updated.email_verification.is_verified,
            is_locked=updated.is_locked(),
            has_two_factor=updated.has_two_factor(),
        )
