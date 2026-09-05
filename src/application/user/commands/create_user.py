from dataclasses import dataclass
from datetime import UTC, datetime
from typing import final
from uuid import UUID

from application.common.exceptions import TooManyLoginAttemptsError
from application.common.interfaces import (
    RateLimiterInterface,
    UnitOfWorkInterface,
    UUIDGeneratorInterface,
)
from application.user.services import UserService
from domain.user.value_objects import Email, PlainPassword, UserID, Username


@dataclass
class CreateUserInput:
    username: str
    password: str
    email: str | None = None
    ip_address: str | None = None


@final
class CreateUserUseCase:
    def __init__(
        self,
        user_service: UserService,
        uow: UnitOfWorkInterface,
        uuid_generator: UUIDGeneratorInterface,
        rate_limiter: RateLimiterInterface,
    ) -> None:
        self._user_service = user_service
        self._uow = uow
        self._uuid_generator = uuid_generator
        self._rate_limiter = rate_limiter

    async def __call__(self, data: CreateUserInput) -> UUID:
        if data.ip_address:
            limit = await self._rate_limiter.check(f'register:{data.ip_address}')
            if not limit.allowed:
                raise TooManyLoginAttemptsError(limit.retry_after_seconds(datetime.now(UTC)))

        user = await self._user_service.create(
            user_id=UserID(self._uuid_generator()),
            username=Username(data.username),
            email=Email(data.email) if data.email else None,
            password=PlainPassword(data.password),
        )

        await self._uow.commit()

        return user.id.to_raw()
