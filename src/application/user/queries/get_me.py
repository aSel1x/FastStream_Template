from typing import final
from dataclasses import dataclass
from uuid import UUID

from domain.user.exceptions import UserNotFoundError
from domain.user.interfaces.persistence.readers import UserReader
from domain.user.value_objects import UserID


@dataclass
class GetMeOutput:
    user_id: str
    username: str
    email: str | None = None
    is_email_verified: bool = False
    is_locked: bool = False
    has_two_factor: bool = False


@final
class GetMeUseCase:
    def __init__(self, user_reader: UserReader) -> None:
        self._user_reader = user_reader

    async def __call__(self, user_id: UUID) -> GetMeOutput:
        dto = await self._user_reader.get_by_id(UserID(user_id))
        if dto is None:
            raise UserNotFoundError(str(user_id))
        return GetMeOutput(
            user_id=str(dto.user_id),
            username=dto.username or '',
            email=dto.email,
            is_email_verified=dto.is_email_verified,
            is_locked=dto.is_locked,
            has_two_factor=dto.two_factor_secret is not None and dto.two_factor_secret.enabled_at is not None,
        )
