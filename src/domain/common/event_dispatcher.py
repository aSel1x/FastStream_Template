import dataclasses
from dataclasses import dataclass, field
from typing import Self

from domain.common.event import BaseEvent


@dataclass(frozen=True, eq=False)
class DomainEventDispatcher:
    """Records domain events on an immutable entity.

    `_events` is excluded from comparison and repr so `dataclasses.replace` can rebuild the
    entity around it.
    """

    _events: list[BaseEvent] = field(default_factory=list, init=False, compare=False, repr=False)

    def _record_event(self, event: BaseEvent) -> None:
        object.__setattr__(self, '_events', [*self._events, event])

    def pull_events(self) -> list[BaseEvent]:
        events = self._events.copy()
        object.__setattr__(self, '_events', [])
        return events

    def has_events(self) -> bool:
        return len(self._events) > 0

    def _with(self, **changes: object) -> Self:
        """Copy this entity with the given fields replaced, carrying over unpulled events.

        Delegates to `dataclasses.replace`, which rejects unknown field names and runs
        `__post_init__`. The hand-rolled `__new__` + `__setattr__` version this replaces
        accepted a misspelled field silently: it kept the old value, attached a phantom
        attribute, and passed both the type checker and any equality-based test.
        """
        new = dataclasses.replace(self, **changes)
        object.__setattr__(new, '_events', list(self._events))
        return new
