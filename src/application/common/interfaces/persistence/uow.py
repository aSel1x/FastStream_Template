from collections.abc import Awaitable, Callable, Sequence
from types import TracebackType
from typing import Protocol, Self

from domain.common.event import BaseEvent
from domain.common.event_dispatcher import DomainEventDispatcher

EventHandler = Callable[[BaseEvent], Awaitable[None]]


class UnitOfWorkInterface(Protocol):
    """Transaction boundary and the single place domain events are collected.

    Aggregates are `register`ed rather than having their events pulled by hand at each call
    site: a service that mutates an aggregate the use case never sees (revoking sessions on a
    password change, say) would otherwise drop its events silently.
    """

    async def commit(self) -> None:
        """Persist registered events to the outbox, run handlers, and commit."""
        ...

    async def rollback(self) -> None:
        """Roll the transaction back."""
        ...

    def register(self, aggregate: DomainEventDispatcher) -> None:
        """Track an aggregate whose events must be collected on commit."""
        ...

    def add_events(self, events: Sequence[BaseEvent]) -> None:
        """Collect events directly, for the rare caller that has no aggregate to register."""
        ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Commit on a clean exit, roll back on any exception."""
        ...
