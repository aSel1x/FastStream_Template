from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import time
from uuid import UUID, uuid4

from domain.common.json_value import JsonValue


@dataclass
class BaseEvent(ABC):
    event_id: UUID = field(init=False, kw_only=True, default_factory=uuid4)
    event_timestamp: int = field(
        init=False, kw_only=True, default_factory=lambda: int(time())
    )

    @abstractmethod
    def to_payload(self) -> dict[str, JsonValue]:
        """The event's own fields (excluding event_id/event_timestamp), for outbox/audit persistence."""
        ...
