from datetime import datetime
from typing import NamedTuple, Protocol


class RateLimitResult(NamedTuple):
    """The outcome of a rate-limit check.

    Named rather than a bare `(bool, int, datetime | None)`: every call site unpacked the
    last two into `_`, so the remaining count and reset time were computed and thrown away
    instead of becoming the `Retry-After` header the API was missing.
    """

    allowed: bool
    remaining: int
    reset_at: datetime | None

    def retry_after_seconds(self, now: datetime) -> int | None:
        if self.reset_at is None:
            return None
        return max(1, int((self.reset_at - now).total_seconds()))


class RateLimiterInterface(Protocol):
    # Positional-only, so an implementation is free to name its parameter whatever reads best
    # without breaking structural compatibility.
    async def check(self, key: str, /) -> RateLimitResult: ...

    async def reset(self, key: str, /) -> None: ...


class LoginAttemptLimiterInterface(Protocol):
    """Counts failed logins per bucket.

    The bucket is `(client ip, identifier)`, not the ip alone: behind a proxy every request
    shares one address, so an ip-only key lets one attacker lock out every user at once.
    """

    async def record_failed_login(self, key: str, /) -> bool: ...

    async def is_locked(self, key: str, /) -> bool: ...

    async def get_remaining_lock_time(self, key: str, /) -> int: ...

    async def reset(self, key: str, /) -> None: ...
