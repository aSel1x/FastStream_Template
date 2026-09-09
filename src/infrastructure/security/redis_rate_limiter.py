from datetime import UTC, datetime, timedelta
from typing import final

import redis.asyncio as redis

from application.common.interfaces.system.rate_limiter import RateLimitResult


@final
class RedisRateLimiter:
    def __init__(
        self,
        redis_client: redis.Redis,
        max_requests: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self._redis = redis_client
        self._max_requests = max_requests
        self._window_seconds = window_seconds

    async def check(self, key: str) -> RateLimitResult:
        now = datetime.now(UTC)
        window_key = f'ratelimit:{key}'

        # INCR is atomic in Redis, so concurrent requests can't both read the
        # same pre-increment count and slip past the limit (unlike a GET-then-INCR pair).
        count = await self._redis.incr(window_key)
        if count == 1:
            _ = await self._redis.expire(window_key, self._window_seconds)

        ttl = await self._redis.ttl(window_key)
        reset_at = now + timedelta(seconds=ttl if ttl > 0 else self._window_seconds)

        if count > self._max_requests:
            return RateLimitResult(allowed=False, remaining=0, reset_at=reset_at)

        remaining = self._max_requests - count
        return RateLimitResult(allowed=True, remaining=remaining, reset_at=reset_at)

    async def reset(self, key: str) -> None:
        _ = await self._redis.delete(f'ratelimit:{key}')


@final
class RedisLoginAttemptLimiter:
    def __init__(
        self,
        redis_client: redis.Redis,
        max_attempts: int = 5,
        lockout_seconds: int = 900,
    ) -> None:
        self._redis = redis_client
        self._max_attempts = max_attempts
        self._lockout_seconds = lockout_seconds

    async def record_failed_login(self, ip: str) -> bool:
        key = f'login_failed:{ip}'

        pipe = self._redis.pipeline()
        _ = pipe.incr(key)
        _ = pipe.expire(key, self._lockout_seconds, nx=True)
        results: list[object] = list(await pipe.execute())
        count = results[0]
        if not isinstance(count, (int, bytes, str)):
            return False

        return int(count) >= self._max_attempts

    async def is_locked(self, ip: str) -> bool:
        current = await self._redis.get(f'login_failed:{ip}')
        return current is not None and int(current) >= self._max_attempts

    async def get_remaining_lock_time(self, ip: str) -> int:
        ttl = await self._redis.ttl(f'login_failed:{ip}')
        return ttl if ttl > 0 else 0

    async def reset(self, ip: str) -> None:
        _ = await self._redis.delete(f'login_failed:{ip}')
