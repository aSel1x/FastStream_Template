from dataclasses import dataclass
from datetime import UTC, datetime
from typing import final
from uuid import UUID

from application.common.exceptions import TooManyLoginAttemptsError
from application.common.interfaces import (
    LoginAttemptLimiterInterface,
    RateLimiterInterface,
    UnitOfWorkInterface,
)
from application.common.interfaces.system.metrics import MetricsInterface
from application.user.services import UserService
from application.user.two_factor_challenge import TwoFactorChallenge, TwoFactorChallengeStore
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
    #: Set by the Hydra login bridge so a 2FA challenge can resume the flow it interrupted.
    login_challenge: str | None = None


@dataclass
class LoginOutput:
    """The result of a password check.

    Either a usable session, or — when the account has a second factor — a challenge token
    and nothing else. It used to return `requires_two_factor=True` *alongside* a live session
    and refresh token, which made 2FA advisory for every non-browser client.
    """

    user_id: UUID
    session_id: str | None = None
    refresh_token: str | None = None
    requires_two_factor: bool = False
    challenge_token: str | None = None


def _attempt_key(data: LoginInput) -> str | None:
    """The bucket a failed login counts against.

    Pairing the client IP with the identifier being tried keeps one abusive source from
    denying service to every other account behind the same address.
    """
    identifier = data.username or data.email
    if not data.ip_address or not identifier:
        return None
    return f'{data.ip_address}|{identifier.lower()}'


@final
class LoginUseCase:
    def __init__(
        self,
        user_service: UserService,
        rate_limiter: RateLimiterInterface,
        login_attempt_limiter: LoginAttemptLimiterInterface,
        challenges: TwoFactorChallengeStore,
        metrics: MetricsInterface,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._rate_limiter = rate_limiter
        self._login_attempt_limiter = login_attempt_limiter
        self._challenges = challenges
        self._metrics = metrics
        self._uow = uow

    async def __call__(self, data: LoginInput) -> LoginOutput:
        # Keyed on (ip, identifier), not on ip alone. Behind a proxy every request shares one
        # IP, so an ip-only key lets any attacker lock every user out of the service at once.
        attempt_key = _attempt_key(data)
        if attempt_key is not None:
            limit = await self._rate_limiter.check(f'login:{attempt_key}')
            if not limit.allowed:
                self._metrics.rate_limited('login')
                raise TooManyLoginAttemptsError(limit.retry_after_seconds(datetime.now(UTC)))
            if await self._login_attempt_limiter.is_locked(attempt_key):
                self._metrics.rate_limited('login-lockout')
                raise TooManyLoginAttemptsError()

        device_info = DeviceInfo(
            user_agent=data.user_agent,
            ip_address=data.ip_address,
        )

        user, session, refresh_token = await self._user_service.authenticate(
            password=PlainPassword(data.password),
            username=data.username,
            email=data.email,
            device_info=device_info,
        )

        if user is None:
            if attempt_key is not None:
                _ = await self._login_attempt_limiter.record_failed_login(attempt_key)
            self._metrics.login_attempt('unknown_user')
            raise InvalidCredentialsError()

        if session is None:
            if attempt_key is not None:
                _ = await self._login_attempt_limiter.record_failed_login(attempt_key)

            await self._uow.commit()

            # Wrong password / deleted account collapse to the same generic error — this branch
            # is reachable pre-authentication, and account existence is already discoverable via
            # /register's uniqueness check, so hiding it here buys little. Lockout is surfaced
            # distinctly since it's useful, actionable feedback (retry later) rather than a new
            # leak — nothing an attacker couldn't already infer from repeated failed attempts.
            if user.is_locked():
                self._metrics.login_attempt('locked')
                raise AccountLockedError(str(user.id.to_raw()))
            self._metrics.login_attempt('bad_password')
            raise InvalidCredentialsError()

        if attempt_key is not None:
            await self._login_attempt_limiter.reset(attempt_key)

        if user.has_two_factor():
            # The password was right, but that is only the first factor. Nothing usable is
            # handed back and the session is not persisted: the challenge carries what is
            # needed to build it once the second factor checks out.
            await self._uow.commit()
            self._metrics.login_attempt('two_factor_required')
            token = await self._challenges.issue(
                TwoFactorChallenge(
                    user_id=user.id.to_raw(),
                    device_info=device_info,
                    login_challenge=data.login_challenge,
                )
            )
            return LoginOutput(
                user_id=user.id.to_raw(),
                requires_two_factor=True,
                challenge_token=token,
            )

        await self._user_service.persist_session(session)
        await self._uow.commit()
        self._metrics.login_attempt('success')
        self._metrics.session_created()

        return LoginOutput(
            user_id=user.id.to_raw(),
            session_id=str(session.session_id),
            refresh_token=refresh_token,
        )
