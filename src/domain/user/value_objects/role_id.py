from dataclasses import dataclass
from typing import override
from uuid import UUID

from domain.common.exceptions import BaseDomainError
from domain.common.value_object import ValueObject


@dataclass(eq=False)
class WrongRoleIDError(BaseDomainError):
    role_id: object

    @property
    @override
    def detail(self) -> str:
        return f'Invalid role ID "{self.role_id}"'


NIL_UUID = UUID(int=0)


@dataclass(frozen=True, init=False)
class RoleID(ValueObject[UUID]):
    value: UUID

    def __init__(self, value: object) -> None:
        if not isinstance(value, UUID):
            raise WrongRoleIDError(value)
        super().__init__(value)

    @override
    def _validate(self) -> None:
        if self.value == NIL_UUID:
            raise WrongRoleIDError(self.value)
