from abc import ABC

from .event import BaseEvent


class BaseService(ABC):
    def __init__(self) -> None:
        self._events: list[BaseEvent] = []

    def _record_event(self, event: BaseEvent) -> None:
        self._events.append(event)

    def get_events(self) -> list[BaseEvent]:
        return self._events

    def clear_events(self) -> None:
        self._events.clear()

    def pull_events(self) -> list[BaseEvent]:
        events = self.get_events().copy()
        self.clear_events()
        return events
