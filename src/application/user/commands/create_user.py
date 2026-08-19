from typing import final
from dataclasses import dataclass
from uuid import UUID

from application.common.exceptions import TooManyLoginAttemptsError
from application.common.interfaces import RateLimiterInterface, UnitOfWorkInterface, UUIDGeneratorInterface
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

    async def __call__(self, input: CreateUserInput) -> UUID:
        if input.ip_address:
            allowed, _, _ = await self._rate_limiter.check(f'register:{input.ip_address}')
            if not allowed:
                raise TooManyLoginAttemptsError()

        user = await self._user_service.create(
            user_id=UserID(self._uuid_generator()),
            username=Username(input.username),
            email=Email(input.email) if input.email else None,
            password=PlainPassword(input.password),
        )

        self._uow.add_events(user.pull_events())
        await self._uow.commit()

        return user.id.to_raw()
