from typing import final
from dataclasses import dataclass
from uuid import UUID

from application.common.exceptions import TooManyLoginAttemptsError
from application.common.interfaces import RateLimiterInterface, UnitOfWorkInterface
from application.user.services import UserService
from domain.user.value_objects import Email, PlainPassword, UserID


@dataclass
class RequestPasswordResetInput:
    email: str
    ip_address: str | None = None


@dataclass
class RequestPasswordResetOutput:
    success: bool


@final
class RequestPasswordResetUseCase:
    def __init__(
        self,
        user_service: UserService,
        uow: UnitOfWorkInterface,
        rate_limiter: RateLimiterInterface,
    ) -> None:
        self._user_service = user_service
        self._uow = uow
        self._rate_limiter = rate_limiter

    async def __call__(self, input: RequestPasswordResetInput) -> RequestPasswordResetOutput:
        if input.ip_address:
            allowed, _, _ = await self._rate_limiter.check(f'password-reset-request:{input.ip_address}')
            if not allowed:
                raise TooManyLoginAttemptsError()

        user = await self._user_service.request_password_reset(
            Email(input.email),
        )

        if user:
            self._uow.add_events(user.pull_events())
            await self._uow.commit()

        return RequestPasswordResetOutput(success=True)


@dataclass
class ResetPasswordInput:
    user_id: str
    token: str
    new_password: str
    ip_address: str | None = None


@dataclass
class ResetPasswordOutput:
    success: bool


@final
class ResetPasswordUseCase:
    def __init__(
        self,
        user_service: UserService,
        uow: UnitOfWorkInterface,
        rate_limiter: RateLimiterInterface,
    ) -> None:
        self._user_service = user_service
        self._uow = uow
        self._rate_limiter = rate_limiter

    async def __call__(self, input: ResetPasswordInput) -> ResetPasswordOutput:
        if input.ip_address:
            allowed, _, _ = await self._rate_limiter.check(f'password-reset-confirm:{input.ip_address}')
            if not allowed:
                raise TooManyLoginAttemptsError()

        user = await self._user_service.reset_password(
            user_id=UserID(UUID(input.user_id)),
            token=input.token,
            new_password=PlainPassword(input.new_password),
        )

        self._uow.add_events(user.pull_events())
        await self._uow.commit()

        return ResetPasswordOutput(success=True)
