import datetime as dt
from abc import ABC
from dataclasses import dataclass, field
from functools import partial
from typing import override
from uuid import UUID, uuid4

from domain.common.value_object import BaseValueObject

datetime_utcnow = partial(dt.datetime.now, tz=dt.timezone.utc)


@dataclass(frozen=True)
class EntityUUID(BaseValueObject[UUID]):
    @override
    def _validate(self) -> None:
        return super()._validate()

    @classmethod
    def create(cls) -> 'EntityUUID':
        return cls(uuid4())


@dataclass(frozen=True)
class CreatedAt(BaseValueObject[dt.datetime]):
    @override
    def _validate(self) -> None:
        return super()._validate()

    @classmethod
    def create(cls) -> 'CreatedAt':
        return cls(dt.datetime.now(dt.timezone.utc))


@dataclass(frozen=True)
class UpdatedAt(BaseValueObject[dt.datetime]):
    @override
    def _validate(self) -> None:
        return super()._validate()

    @classmethod
    def create(cls) -> 'UpdatedAt':
        return cls(dt.datetime.now(dt.timezone.utc))


@dataclass
class BaseEntity(ABC):
    pass


@dataclass
class UUIDMixin:
    uuid: EntityUUID = field(
        init=False, kw_only=True, default_factory=EntityUUID.create
    )


@dataclass
class AuditMixin:
    created_at: CreatedAt = field(
        init=False, kw_only=True, default_factory=CreatedAt.create
    )
    updated_at: UpdatedAt = field(
        init=False, kw_only=True, default_factory=UpdatedAt.create
    )
