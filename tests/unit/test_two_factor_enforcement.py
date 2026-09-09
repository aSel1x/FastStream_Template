"""Two-factor authentication must be mandatory, not advisory.

The direct JSON API used to return `requires_two_factor: true` alongside a live session and
refresh token, and offered no endpoint to complete the second step — so any non-browser client
was authenticated on the password alone.
"""

from typing import final
from unittest.mock import AsyncMock
from uuid import uuid4

import pyotp
import pytest

from application.common.interfaces.system.rate_limiter import RateLimitResult
from application.user.commands.complete_two_factor import (
    CompleteTwoFactorInput,
    CompleteTwoFactorUseCase,
)
from application.user.commands.login import LoginInput, LoginUseCase
from application.user.replay_guard import UsedCodeRegistry
from application.user.two_factor_challenge import (
    MAX_ATTEMPTS,
    TwoFactorChallengeExpiredError,
)
from domain.user.entities.session import DeviceInfo, SessionAggregate
from domain.user.entities.user import User
from domain.user.value_objects import Email, HashedPassword, UserID, Username
from infrastructure.cache.memory_cache import InMemoryCache
from infrastructure.db.memory.uow import InMemoryUoW
from infrastructure.observability.prometheus_metrics import NullMetrics
from infrastructure.two_factor import TwoFactorAuth
from infrastructure.two_factor_challenge_store import CachedTwoFactorChallengeStore


def _enrolled_user() -> tuple[User, str]:
    """A user with an active second factor, and its TOTP secret."""
    two_factor = TwoFactorAuth()
    user = User.create(
        user_id=UserID(uuid4()),
        username=Username('testuser'),
        email=Email('test@example.com'),
        hashed_password=HashedPassword(b'hashed'),
        verification_token='token',
    )
    pending, _codes = user.begin_two_factor_enrolment(two_factor)
    assert pending.two_factor_secret is not None
    secret = pending.two_factor_secret.secret
    enabled = pending.confirm_two_factor(pyotp.TOTP(secret).now(), two_factor)
    _ = enabled.pull_events()
    return enabled, secret


@final
class _Harness:
    def __init__(self, user: User) -> None:
        self.cache = InMemoryCache()
        self.challenges = CachedTwoFactorChallengeStore(self.cache)
        self.uow = InMemoryUoW()
        self.user = user

        self.user_service = AsyncMock()
        self.user_service.authenticate = AsyncMock(
            return_value=(
                user,
                SessionAggregate.create(user_id=user.id, device_info=DeviceInfo()),
                'raw-refresh',
            )
        )
        self.user_service.start_session = AsyncMock(
            return_value=(
                SessionAggregate.create(user_id=user.id, device_info=DeviceInfo()),
                'issued-refresh',
            )
        )
        self.user_repo = AsyncMock()
        self.user_repo.acquire_by_id = AsyncMock(return_value=user)
        self.user_repo.update = AsyncMock()

        limiter = AsyncMock()
        limiter.check = AsyncMock(return_value=RateLimitResult(True, 10, None))
        attempts = AsyncMock()
        attempts.is_locked = AsyncMock(return_value=False)
        attempts.reset = AsyncMock()

        self.login = LoginUseCase(
            user_service=self.user_service,
            rate_limiter=limiter,
            login_attempt_limiter=attempts,
            challenges=self.challenges,
            metrics=NullMetrics(),
            uow=self.uow,
        )
        self.complete = CompleteTwoFactorUseCase(
            user_service=self.user_service,
            user_repo=self.user_repo,
            two_factor=TwoFactorAuth(),
            challenges=self.challenges,
            used_codes=UsedCodeRegistry(self.cache),
            uow=self.uow,
        )


class TestDirectApiLogin:
    @pytest.mark.asyncio
    async def test_password_alone_yields_no_session(self) -> None:
        user, _secret = _enrolled_user()
        harness = _Harness(user)

        result = await harness.login(LoginInput(password='Test@1234', username='testuser'))

        assert result.requires_two_factor is True
        assert result.challenge_token, 'the caller needs a handle to complete the second step'
        assert result.session_id is None, 'a session before the second factor defeats 2FA'
        assert result.refresh_token is None
        harness.user_service.persist_session.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_valid_code_completes_the_login(self) -> None:
        user, secret = _enrolled_user()
        harness = _Harness(user)
        issued = await harness.login(LoginInput(password='Test@1234', username='testuser'))
        assert issued.challenge_token is not None

        result = await harness.complete(
            CompleteTwoFactorInput(
                challenge_token=issued.challenge_token,
                code=pyotp.TOTP(secret).now(),
            )
        )

        assert result.session_id
        assert result.refresh_token == 'issued-refresh'

    @pytest.mark.asyncio
    async def test_a_code_cannot_be_replayed(self) -> None:
        user, secret = _enrolled_user()
        harness = _Harness(user)
        first = await harness.login(LoginInput(password='Test@1234', username='testuser'))
        assert first.challenge_token is not None
        code = pyotp.TOTP(secret).now()
        _ = await harness.complete(
            CompleteTwoFactorInput(challenge_token=first.challenge_token, code=code)
        )

        second = await harness.login(LoginInput(password='Test@1234', username='testuser'))
        assert second.challenge_token is not None
        with pytest.raises(TwoFactorChallengeExpiredError):
            # Still inside the TOTP window, so the code would otherwise verify again.
            _ = await harness.complete(
                CompleteTwoFactorInput(challenge_token=second.challenge_token, code=code)
            )

    @pytest.mark.asyncio
    async def test_a_used_challenge_is_gone(self) -> None:
        user, secret = _enrolled_user()
        harness = _Harness(user)
        issued = await harness.login(LoginInput(password='Test@1234', username='testuser'))
        assert issued.challenge_token is not None
        _ = await harness.complete(
            CompleteTwoFactorInput(
                challenge_token=issued.challenge_token,
                code=pyotp.TOTP(secret).now(),
            )
        )

        with pytest.raises(TwoFactorChallengeExpiredError):
            _ = await harness.complete(
                CompleteTwoFactorInput(
                    challenge_token=issued.challenge_token,
                    code=pyotp.TOTP(secret).now(),
                )
            )

    @pytest.mark.asyncio
    async def test_guessing_burns_the_challenge(self) -> None:
        user, _secret = _enrolled_user()
        harness = _Harness(user)
        issued = await harness.login(LoginInput(password='Test@1234', username='testuser'))
        assert issued.challenge_token is not None

        for _ in range(MAX_ATTEMPTS):
            with pytest.raises(TwoFactorChallengeExpiredError):
                _ = await harness.complete(
                    CompleteTwoFactorInput(challenge_token=issued.challenge_token, code='000000')
                )

        assert await harness.cache.get(f'pending_2fa:{issued.challenge_token}') is None, (
            'a six-digit code is guessable in far fewer tries than a per-IP limit allows'
        )


class TestEnrolment:
    def test_enrolment_is_inactive_until_confirmed(self) -> None:
        two_factor = TwoFactorAuth()
        user = User.create(
            user_id=UserID(uuid4()),
            username=Username('testuser'),
            email=Email('test@example.com'),
            hashed_password=HashedPassword(b'hashed'),
            verification_token='token',
        )

        pending, codes = user.begin_two_factor_enrolment(two_factor)

        assert len(codes) == 10
        assert pending.two_factor_secret is not None
        assert pending.has_two_factor() is False, (
            'activating on enrolment locks out anyone whose authenticator missed the secret'
        )

    def test_confirmation_requires_a_valid_code(self) -> None:
        user, _secret = _enrolled_user()
        two_factor = TwoFactorAuth()
        fresh = User.create(
            user_id=UserID(uuid4()),
            username=Username('other'),
            email=Email('other@example.com'),
            hashed_password=HashedPassword(b'hashed'),
            verification_token='token',
        )
        pending, _codes = fresh.begin_two_factor_enrolment(two_factor)

        with pytest.raises(Exception, match='two-factor code'):
            _ = pending.confirm_two_factor('000000', two_factor)

        assert user.has_two_factor() is True
