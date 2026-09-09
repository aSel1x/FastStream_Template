from dataclasses import dataclass
from datetime import UTC, datetime
from typing import final

from application.common.exceptions import TooManyLoginAttemptsError
from application.common.interfaces import RateLimiterInterface, UnitOfWorkInterface
from application.user.services import UserService
from domain.user.value_objects import Email, PlainPassword


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

    async def __call__(self, data: RequestPasswordResetInput) -> RequestPasswordResetOutput:
        if data.ip_address:
            limit = await self._rate_limiter.check(f'password-reset-request:{data.ip_address}')
            if not limit.allowed:
                raise TooManyLoginAttemptsError(limit.retry_after_seconds(datetime.now(UTC)))

        _ = await self._user_service.request_password_reset(Email(data.email))
        await self._uow.commit()

        # Always reports success: telling the caller whether the address exists would turn
        # this endpoint into an account-enumeration oracle.
        return RequestPasswordResetOutput(success=True)


@dataclass
class ResetPasswordInput:
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

    async def __call__(self, data: ResetPasswordInput) -> ResetPasswordOutput:
        if data.ip_address:
            limit = await self._rate_limiter.check(f'password-reset-confirm:{data.ip_address}')
            if not limit.allowed:
                raise TooManyLoginAttemptsError(limit.retry_after_seconds(datetime.now(UTC)))

        _ = await self._user_service.reset_password(
            token=data.token,
            new_password=PlainPassword(data.new_password),
        )

        await self._uow.commit()

        return ResetPasswordOutput(success=True)
