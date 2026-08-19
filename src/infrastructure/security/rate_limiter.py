from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from os import getenv
from typing import Literal, final

from application.common.exceptions import ConfigurationError

RateLimitBackend = Literal['memory', 'redis']


@dataclass
class RateLimitConfig:
    backend: RateLimitBackend = 'memory'
    redis_url: str = 'redis://localhost:6379/0'
    max_requests: int = 100
    window_seconds: int = 60
    max_login_attempts: int = 5
    lockout_seconds: int = 900
    cleanup_interval_seconds: int = 300
    max_keys: int = 10000

    @classmethod
    def from_environ(cls) -> 'RateLimitConfig':
        backend = getenv('RATE_LIMIT_BACKEND', 'memory')
        if backend not in ('memory', 'redis'):
            raise ConfigurationError(f"RATE_LIMIT_BACKEND must be 'memory' or 'redis', got {backend!r}")

        return cls(
            backend=backend,
            redis_url=getenv('REDIS_URL', 'redis://localhost:6379/0'),
            max_requests=int(getenv('RATE_LIMIT_MAX_REQUESTS', '100')),
            window_seconds=int(getenv('RATE_LIMIT_WINDOW_SECONDS', '60')),
            max_login_attempts=int(getenv('RATE_LIMIT_LOGIN_ATTEMPTS', '5')),
            lockout_seconds=int(getenv('RATE_LIMIT_LOCKOUT_SECONDS', '900')),
            cleanup_interval_seconds=int(getenv('RATE_LIMIT_CLEANUP_INTERVAL_SECONDS', '300')),
            max_keys=int(getenv('RATE_LIMIT_MAX_KEYS', '10000')),
        )


@final
class InMemoryRateLimiter:
    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._buckets: dict[str, list[datetime]] = {}
        self._last_cleanup = datetime.now(UTC)

    async def check(self, key: str) -> tuple[bool, int, datetime | None]:
        self._maybe_cleanup()

        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=self._config.window_seconds)

        bucket = self._buckets.setdefault(key, [])
        bucket[:] = [ts for ts in bucket if ts > window_start]

        remaining = self._config.max_requests - len(bucket)

        if len(bucket) >= self._config.max_requests:
            reset_at = min(bucket) + timedelta(seconds=self._config.window_seconds)
            return False, 0, reset_at

        bucket.append(now)
        return True, remaining, now + timedelta(seconds=self._config.window_seconds)

    async def reset(self, key: str) -> None:
        _ = self._buckets.pop(key, None)

    def _maybe_cleanup(self) -> None:
        now = datetime.now(UTC)
        if (now - self._last_cleanup).total_seconds() < self._config.cleanup_interval_seconds:
            return

        self._last_cleanup = now
        window_start = now - timedelta(seconds=self._config.window_seconds * 2)

        expired_keys = [
            k for k, v in self._buckets.items()
            if not v or all(ts < window_start for ts in v)
        ]
        for k in expired_keys:
            del self._buckets[k]

        if len(self._buckets) > self._config.max_keys:
            sorted_keys = sorted(self._buckets.keys(), key=lambda k: self._buckets[k])
            for k in sorted_keys[:len(self._buckets) - self._config.max_keys]:
                del self._buckets[k]


@final
class InMemoryLoginAttemptLimiter:
    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._attempts: dict[str, list[datetime]] = {}
        self._last_cleanup = datetime.now(UTC)

    async def record_failed_login(self, ip: str) -> bool:
        self._maybe_cleanup()

        now = datetime.now(UTC)
        window_start = now - timedelta(seconds=self._config.lockout_seconds)

        attempts = self._attempts.setdefault(ip, [])
        attempts.append(now)
        attempts[:] = [ts for ts in attempts if ts > window_start]

        return len(attempts) >= self._config.max_login_attempts

    async def is_locked(self, ip: str) -> bool:
        recent = self._recent_attempts(ip)
        return len(recent) >= self._config.max_login_attempts

    async def get_remaining_lock_time(self, ip: str) -> int:
        recent = self._recent_attempts(ip)
        if not recent:
            return 0

        lock_end = min(recent) + timedelta(seconds=self._config.lockout_seconds)
        remaining = (lock_end - datetime.now(UTC)).total_seconds()
        return max(0, int(remaining))

    async def reset(self, ip: str) -> None:
        _ = self._attempts.pop(ip, None)

    def _recent_attempts(self, ip: str) -> list[datetime]:
        if ip not in self._attempts:
            return []

        window_start = datetime.now(UTC) - timedelta(seconds=self._config.lockout_seconds)
        return [ts for ts in self._attempts[ip] if ts > window_start]

    def _maybe_cleanup(self) -> None:
        now = datetime.now(UTC)
        if (now - self._last_cleanup).total_seconds() < self._config.cleanup_interval_seconds:
            return

        self._last_cleanup = now
        window_start = now - timedelta(seconds=self._config.lockout_seconds * 2)

        expired_ips = [
            ip for ip, attempts in self._attempts.items()
            if not attempts or all(ts < window_start for ts in attempts)
        ]
        for ip in expired_ips:
            del self._attempts[ip]

        if len(self._attempts) > self._config.max_keys:
            sorted_ips = sorted(self._attempts.keys(), key=lambda ip: self._attempts[ip])
            for ip in sorted_ips[:len(self._attempts) - self._config.max_keys]:
                del self._attempts[ip]
