# pyright: reportUnsafeMultipleInheritance = false

from dataclasses import dataclass
from typing import override
from uuid import UUID

from domain.common.exceptions import BaseDomainError
from domain.common.value_object import ValueObject


@dataclass(eq=False)
class WrongUserIDError(ValueError, BaseDomainError):
    user_id: UUID

    @property
    @override
    def detail(self) -> str:
        return f'Invalid user ID "{self.user_id}"'


@dataclass(frozen=True)
class UserID(ValueObject[UUID]):
    value: UUID

    @override
    def _validate(self) -> None:
        if not self.value:
            raise WrongUserIDError(self.value)
