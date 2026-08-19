from typing import final
from dataclasses import dataclass
from uuid import UUID

from application.common.exceptions import TooManyLoginAttemptsError
from application.common.interfaces import (
    LoginAttemptLimiterInterface,
    RateLimiterInterface,
    UnitOfWorkInterface,
)
from application.user.services import UserService
from domain.user.entities.session import DeviceInfo
from domain.user.exceptions import AccountLockedError, InvalidCredentialsError
from domain.user.value_objects import PlainPassword


@dataclass
class LoginInput:
    password: str
    username: str | None = None
    email: str | None = None
    user_agent: str | None = None
    ip_address: str | None = None


@dataclass
class LoginOutput:
    user_id: UUID
    session_id: str
    refresh_token: str | None = None
    requires_two_factor: bool = False


@final
class LoginUseCase:
    def __init__(
        self,
        user_service: UserService,
        rate_limiter: RateLimiterInterface,
        login_attempt_limiter: LoginAttemptLimiterInterface,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._rate_limiter = rate_limiter
        self._login_attempt_limiter = login_attempt_limiter
        self._uow = uow

    async def __call__(self, input: LoginInput) -> LoginOutput:
        if input.ip_address:
            allowed, _, _ = await self._rate_limiter.check(f'login:{input.ip_address}')
            if not allowed:
                raise TooManyLoginAttemptsError()
            if await self._login_attempt_limiter.is_locked(input.ip_address):
                raise TooManyLoginAttemptsError()

        device_info = DeviceInfo(
            user_agent=input.user_agent,
            ip_address=input.ip_address,
        )

        user, session, refresh_token = await self._user_service.authenticate(
            password=PlainPassword(input.password),
            username=input.username,
            email=input.email,
            device_info=device_info,
        )

        if user is None:
            if input.ip_address:
                _ = await self._login_attempt_limiter.record_failed_login(input.ip_address)
            raise InvalidCredentialsError()

        if session is None:
            if input.ip_address:
                _ = await self._login_attempt_limiter.record_failed_login(input.ip_address)

            self._uow.add_events(user.pull_events())
            await self._uow.commit()

            # Wrong password / deleted account collapse to the same generic error — this branch
            # is reachable pre-authentication, and account existence is already discoverable via
            # /register's uniqueness check, so hiding it here buys little. Lockout is surfaced
            # distinctly since it's useful, actionable feedback (retry later) rather than a new
            # leak — nothing an attacker couldn't already infer from repeated failed attempts.
            if user.is_locked():
                raise AccountLockedError(str(user.id.to_raw()))
            raise InvalidCredentialsError()

        if input.ip_address:
            await self._login_attempt_limiter.reset(input.ip_address)

        await self._user_service.persist_session(session)

        self._uow.add_events(user.pull_events())
        self._uow.add_events(session.pull_events())
        await self._uow.commit()

        return LoginOutput(
            user_id=user.id.to_raw(),
            session_id=str(session.session_id),
            refresh_token=refresh_token,
            requires_two_factor=user.has_two_factor(),
        )
