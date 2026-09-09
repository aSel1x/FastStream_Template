from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from time import time
from typing import ClassVar
from uuid import UUID, uuid4

from domain.common.json_value import JsonValue


@dataclass
class BaseEvent(ABC):
    #: The name this event is published under. Defaults to the class name, but declared
    #: explicitly so renaming the class does not silently rename the wire contract, and so
    #: consumers bind to a value rather than to a Python identifier.
    event_name: ClassVar[str] = ''

    #: Payload keys that carry a live credential. They are stored in the outbox only long
    #: enough for the worker to render an email: never published to the broker, and scrubbed
    #: from the row once the event is handled.
    sensitive_fields: ClassVar[frozenset[str]] = frozenset()

    event_id: UUID = field(init=False, kw_only=True, default_factory=uuid4)
    event_timestamp: int = field(init=False, kw_only=True, default_factory=lambda: int(time()))

    @classmethod
    def wire_name(cls) -> str:
        """The routing key and stored `event_type` for this event."""
        return cls.event_name or cls.__name__

    @abstractmethod
    def to_payload(self) -> dict[str, JsonValue]:
        """The event's own fields, for outbox/audit persistence.

        Excludes event_id/event_timestamp.
        """
        ...
