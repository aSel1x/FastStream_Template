import secrets
from typing import ClassVar, final, override
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

from application.common.interfaces.system.cache import CacheInterface
from application.user.two_factor_challenge import (
    CHALLENGE_TTL_SECONDS,
    TwoFactorChallenge,
    TwoFactorChallengeExpiredError,
    TwoFactorChallengeStore,
)
from domain.user.entities.session import DeviceInfo

_CACHE_PREFIX = 'pending_2fa:'


class _StoredChallenge(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra='ignore')

    user_id: UUID
    user_agent: str | None = None
    ip_address: str | None = None
    attempts: int = 0
    login_challenge: str | None = None

    @classmethod
    def of(cls, challenge: TwoFactorChallenge) -> _StoredChallenge:
        return cls(
            user_id=challenge.user_id,
            user_agent=challenge.device_info.user_agent,
            ip_address=challenge.device_info.ip_address,
            attempts=challenge.attempts,
            login_challenge=challenge.login_challenge,
        )

    def to_challenge(self) -> TwoFactorChallenge:
        return TwoFactorChallenge(
            user_id=self.user_id,
            device_info=DeviceInfo(user_agent=self.user_agent, ip_address=self.ip_address),
            attempts=self.attempts,
            login_challenge=self.login_challenge,
        )


@final
class CachedTwoFactorChallengeStore(TwoFactorChallengeStore):
    """Keeps pending challenges in the cache.

    With the Redis backend this works across replicas; the in-memory backend does not, which
    is why it is only a development default.
    """

    def __init__(self, cache: CacheInterface) -> None:
        self._cache = cache

    @override
    async def issue(self, challenge: TwoFactorChallenge) -> str:
        token = secrets.token_urlsafe(32)
        await self._cache.set(
            _CACHE_PREFIX + token,
            _StoredChallenge.of(challenge).model_dump_json(),
            ttl_seconds=CHALLENGE_TTL_SECONDS,
        )
        return token

    @override
    async def read(self, token: str) -> TwoFactorChallenge:
        raw = await self._cache.get(_CACHE_PREFIX + token)
        if raw is None:
            raise TwoFactorChallengeExpiredError()
        try:
            return _StoredChallenge.model_validate_json(raw).to_challenge()
        except ValidationError as exc:
            await self.discard(token)
            raise TwoFactorChallengeExpiredError() from exc

    @override
    async def record_failure(self, token: str, challenge: TwoFactorChallenge) -> None:
        updated = challenge.with_failed_attempt()
        if updated.is_exhausted():
            await self.discard(token)
            raise TwoFactorChallengeExpiredError()
        await self._cache.set(
            _CACHE_PREFIX + token,
            _StoredChallenge.of(updated).model_dump_json(),
            ttl_seconds=CHALLENGE_TTL_SECONDS,
        )

    @override
    async def discard(self, token: str) -> None:
        await self._cache.delete(_CACHE_PREFIX + token)
