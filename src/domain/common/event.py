from abc import ABC
from dataclasses import dataclass, field
from time import time
from uuid import UUID, uuid4


@dataclass
class BaseEvent(ABC):
    event_id: UUID = field(init=False, kw_only=True, default_factory=uuid4)
    event_timestamp: int = field(
        init=False, kw_only=True, default_factory=lambda: int(time())
    )
