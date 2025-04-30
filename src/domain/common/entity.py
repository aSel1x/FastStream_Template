import datetime as dt
from abc import ABC
from dataclasses import dataclass, field
from functools import partial
from uuid import UUID, uuid4

datetime_utcnow = partial(dt.datetime.now, tz=dt.timezone.utc)


@dataclass
class BaseEntity(ABC):
    pass


@dataclass
class UUIDMixin:
    uuid: UUID = field(init=False, kw_only=True, default_factory=uuid4)


@dataclass
class AuditMixin:
    created_at: dt.datetime = field(
        init=False, kw_only=True, default_factory=datetime_utcnow
    )
    updated_at: dt.datetime = field(
        init=False, kw_only=True, default_factory=datetime_utcnow
    )
