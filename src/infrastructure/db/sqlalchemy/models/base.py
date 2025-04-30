import datetime as dt
from uuid import UUID

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, registry
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime

convention = {
    'ix': 'ix_%(column_0_label)s',  # INDEX
    'uq': 'uq_%(table_name)s_%(column_0_N_name)s',  # UNIQUE
    'ck': 'ck_%(table_name)s_%(constraint_name)s',  # CHECK
    'fk': 'fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s',  # FOREIGN KEY
    'pk': 'pk_%(table_name)s',  # PRIMARY KEY
}

metadata = MetaData(naming_convention=convention)

mapper_registry = registry(metadata=metadata)


class BaseModel(DeclarativeBase):
    registry = mapper_registry
    metadata = metadata


class UUIDMixin(BaseModel):
    __abstract__ = True

    uuid: Mapped[UUID] = mapped_column(
        primary_key=True,
        unique=True,
        nullable=False,
    )


class AuditMixin(BaseModel):
    __abstract__ = True

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
