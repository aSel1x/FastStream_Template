from abc import ABC
from dataclasses import dataclass, field
from typing import Self

from domain.common.event import BaseEvent


@dataclass(frozen=True, eq=False)
class DomainEventDispatcher(ABC):
    _events: list[BaseEvent] = field(default_factory=list, init=False)

    def _record_event(self, event: BaseEvent) -> None:
        object.__setattr__(self, '_events', self._events + [event])

    def pull_events(self) -> list[BaseEvent]:
        events = self._events.copy()
        object.__setattr__(self, '_events', [])
        return events

    def has_events(self) -> bool:
        return len(self._events) > 0

    def _own_fields(self) -> dict[str, object]:
        raw: dict[str, object] = dict(self.__dict__)
        return {k: v for k, v in raw.items() if not k.startswith('_')}

    def _with(self, **kwargs: object) -> Self:
        """Return a copy of this entity with the given fields replaced, carrying over any unpulled events."""
        cls = type(self)
        current = self._own_fields()
        current.update(kwargs)
        new = cls.__new__(cls)
        for k, v in current.items():
            object.__setattr__(new, k, v)
        object.__setattr__(new, '_events', list(self._events))
        return new