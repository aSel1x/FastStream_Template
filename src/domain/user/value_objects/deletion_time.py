from datetime import UTC, datetime
from typing import Self, override

from domain.common.value_object import BaseValueObject


class DeletionTime(BaseValueObject[datetime | None]):
    value: datetime | None

    @override
    def _validate(self) -> None:
        pass

    @classmethod
    def create_deleted(cls) -> Self:
        return cls(datetime.now(UTC))

    @classmethod
    def create_not_deleted(cls) -> Self:
        return cls(None)

    def is_deleted(self) -> bool:
        return self.value is not None
