from datetime import UTC, datetime
from typing import Protocol, final, override


class Clock(Protocol):
    """The current time, as a dependency.

    Reading the wall clock directly inside an entity makes expiry logic untestable without
    sleeping or monkeypatching: a lockout window, a token TTL and a session expiry all become
    "wait and see". Passing the clock in lets a test say exactly what time it is.
    """

    def now(self) -> datetime:
        """The current instant, always timezone-aware and in UTC."""
        ...


@final
class SystemClock(Clock):
    @override
    def now(self) -> datetime:
        return datetime.now(UTC)


@final
class FrozenClock(Clock):
    """A clock that only moves when told to. For tests."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            message = 'FrozenClock needs an aware datetime; a naive one silently means UTC'
            raise ValueError(message)
        self._at = at

    @override
    def now(self) -> datetime:
        return self._at

    def advance(self, seconds: float) -> None:
        from datetime import timedelta

        self._at += timedelta(seconds=seconds)
