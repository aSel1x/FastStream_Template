from abc import ABC
from typing import ClassVar

from .event import BaseEvent


class BaseService(ABC):
    """Base service class with event tracking.

    All service instances are automatically tracked in _instances registry
    for event collection by UnitOfWork.
    """

    _instances: ClassVar[list['BaseService']] = []

    def __init__(self) -> None:
        self._events: list[BaseEvent] = []
        BaseService._instances.append(self)

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

    @classmethod
    def collect_all_events(cls) -> list[BaseEvent]:
        """Collect events from all registered service instances."""
        events: list[BaseEvent] = []
        for service in cls._instances:
            events.extend(service.pull_events())
        return events

    @classmethod
    def clear_all_events(cls) -> None:
        """Clear events from all registered service instances."""
        for service in cls._instances:
            service.clear_events()
