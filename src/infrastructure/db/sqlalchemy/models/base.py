import abc
from dataclasses import dataclass
from typing import Any

from domain.common.entity import BaseEntity
from domain.common.value_object import ValueObject

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.orm import (
    Composite,
    DeclarativeBase,
    Mapper,
    registry,
)

convention = {
    'ix': 'ix_%(column_0_label)s',  # INDEX
    'uq': 'uq_%(table_name)s_%(column_0_N_name)s',  # UNIQUE
    'ck': 'ck_%(table_name)s_%(constraint_name)s',  # CHECK
    'fk': 'fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s',  # FOREIGN KEY
    'pk': 'pk_%(table_name)s',  # PRIMARY KEY
}


mapper_registry = registry(metadata=MetaData(naming_convention=convention))

CT = ValueObject[Any]  # pyright: ignore[reportExplicitAny]
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
