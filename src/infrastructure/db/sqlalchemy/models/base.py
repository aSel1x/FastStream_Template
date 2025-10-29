import abc
import datetime as dt
from dataclasses import dataclass
from typing import Any, override
from uuid import UUID

from domain.common.entity import BaseEntity, CreatedAt, EntityUUID, UpdatedAt
from domain.common.value_object import BaseValueObject

from sqlalchemy import Column, MetaData, Table
from sqlalchemy import types as sa_types
from sqlalchemy.orm import (
    Composite,
    DeclarativeBase,
    Mapper,
    composite,
    registry,
)
from sqlalchemy.sql import func

convention = {
    'ix': 'ix_%(column_0_label)s',  # INDEX
    'uq': 'uq_%(table_name)s_%(column_0_N_name)s',  # UNIQUE
    'ck': 'ck_%(table_name)s_%(constraint_name)s',  # CHECK
    'fk': 'fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s',  # FOREIGN KEY
    'pk': 'pk_%(table_name)s',  # PRIMARY KEY
}


mapper_registry = registry(metadata=MetaData(naming_convention=convention))

CT = BaseValueObject[Any]  # pyright: ignore[reportExplicitAny]
AnyCol = Column[Any]  # pyright: ignore[reportExplicitAny]


class BaseModel(DeclarativeBase):
    registry = mapper_registry  # pyright: ignore[reportUnannotatedClassAttribute]
    metadata = mapper_registry.metadata  # pyright: ignore[reportUnannotatedClassAttribute]


@dataclass
class ImperativeMixin(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def columns(cls) -> list[AnyCol]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def vo_map(cls, table: Table) -> dict[str, Composite[CT]]:
        raise NotImplementedError


class UUIDMixin(ImperativeMixin):
    @classmethod
    @override
    def columns(cls) -> list[Column[UUID]]:
        return [
            Column(
                'uuid',
                sa_types.UUID(as_uuid=True),
                primary_key=True,
                unique=True,
                nullable=False,
            )
        ]

    @classmethod
    @override
    def vo_map(cls, table: Table) -> dict[str, Composite[CT]]:
        return {'uuid': composite(EntityUUID, table.c.uuid)}


class AuditMixin(ImperativeMixin):
    @classmethod
    @override
    def columns(cls) -> list[Column[dt.datetime]]:
        return [
            Column(
                'created_at',
                sa_types.DateTime(timezone=True),
                server_default=func.now(),
            ),
            Column(
                'updated_at',
                sa_types.DateTime(timezone=True),
                server_default=func.now(),
                onupdate=func.now(),
            ),
        ]

    @classmethod
    @override
    def vo_map(cls, table: Table) -> dict[str, Composite[CT]]:
        return {
            'created_at': composite(CreatedAt, table.c.created_at),
            'updated_at': composite(UpdatedAt, table.c.updated_at),
        }


def create_table(
    name: str, *columns: AnyCol, mixins: set[type[ImperativeMixin]] | None = None
) -> Table:
    mixins = mixins or set()

    all_columns: list[AnyCol] = []

    for mixin in mixins:
        all_columns.extend(mixin.columns())

    all_columns.extend(columns)

    return Table(
        name,
        BaseModel.metadata,
        *all_columns,
    )


def create_mapping(
    entity_class: type[BaseEntity],
    table: Table,
    properties: dict[str, Composite[CT]],
    mixins: set[type[ImperativeMixin]] | None = None,
    column_prefix: str = '_',
) -> Mapper[BaseEntity]:
    mixins = mixins or set()

    _properties: dict[str, Composite[CT]] = {}
    for mixin in mixins:
        _properties.update(mixin.vo_map(table))

    _properties.update(properties)

    return mapper_registry.map_imperatively(
        entity_class,
        table,
        properties=_properties,
        column_prefix=column_prefix,
    )
