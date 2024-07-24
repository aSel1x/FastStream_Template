import datetime as dt

from sqlalchemy.types import BigInteger, TypeDecorator


class Unixepoch(TypeDecorator):
    impl = BigInteger
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(BigInteger())

    def process_bind_param(self, value: dt.datetime | dt.date | str | None, dialect) -> int | None:
        if isinstance(value, dt.datetime):
            return int(value.timestamp())
        elif isinstance(value, dt.date):
            return int(dt.datetime.combine(value, dt.time.min).timestamp())
        elif isinstance(value, str):
            return int(dt.datetime.fromisoformat(value).timestamp())

    def process_result_value(self, value: int, dialect) -> dt.datetime | None:
        if isinstance(value, int):
            return dt.datetime.fromtimestamp(value, dt.UTC)
