from collections.abc import Awaitable, Callable
from typing import Protocol

from domain.common.event import BaseEvent


EventHandler = Callable[[BaseEvent], Awaitable[None]]


class UnitOfWorkInterface(Protocol):
    async def commit(self) -> None:
        """Commit transaction and publish domain events."""
        ...

    async def rollback(self) -> None:
        """Rollback transaction."""
        ...

    def add_events(self, events: list[BaseEvent]) -> None:
        """Collect domain events for outbox persistence on commit."""
        ...
