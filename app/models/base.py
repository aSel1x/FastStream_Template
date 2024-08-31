import datetime as dt
import uuid
from functools import partial

from sqlalchemy import Column as saColumn
from sqlmodel import Field, SQLModel

from . import types

datetime_utcnow = partial(dt.datetime.now, tz=dt.UTC)


class IDModel(SQLModel):
    id: int | None = Field(
        default=None,
        primary_key=True,
        nullable=False,
        index=True,
    )


class UUIDModel(SQLModel):
    external_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        unique=True,
        nullable=False
    )


class TimestampModel(SQLModel):
    created_at: dt.datetime | int | str = Field(
        default_factory=datetime_utcnow,
        sa_type=types.Unixepoch,
        nullable=False,
    )
    updated_at: dt.datetime | int | str | None = Field(
        sa_column=saColumn(
            default=None,
            type_=types.Unixepoch,
            onupdate=datetime_utcnow,
            nullable=True,
        )
    )

    class Config:
        arbitrary_types_allowed = True
