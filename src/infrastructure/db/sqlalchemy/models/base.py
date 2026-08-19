from typing import ClassVar

from sqlalchemy import MetaData, Table
from sqlalchemy.orm import DeclarativeBase, registry
from sqlalchemy.sql.schema import SchemaItem

convention = {
    'ix': 'ix_%(column_0_label)s',  # INDEX
    'uq': 'uq_%(table_name)s_%(column_0_N_name)s',  # UNIQUE
    'ck': 'ck_%(table_name)s_%(constraint_name)s',  # CHECK
    'fk': 'fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s',  # FOREIGN KEY
    'pk': 'pk_%(table_name)s',  # PRIMARY KEY
}


mapper_registry = registry(metadata=MetaData(naming_convention=convention))


class BaseModel(DeclarativeBase):
    registry: ClassVar[registry] = mapper_registry
    metadata: ClassVar[MetaData] = mapper_registry.metadata


def create_table(name: str, *columns: SchemaItem) -> Table:
    return Table(
        name,
        BaseModel.metadata,
        *columns,
    )
