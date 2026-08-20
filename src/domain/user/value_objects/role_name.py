import re
from dataclasses import dataclass
from typing import ClassVar, override

from domain.common.exceptions import BaseDomainError
from domain.common.value_object import ValueObject

ROLE_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{2,31}$')


@dataclass(eq=False)
class WrongRoleNameError(BaseDomainError):
    status: ClassVar[int] = 400
    name: str

    @property
    @override
    def detail(self) -> str:
        return f'Invalid role name "{self.name}"'


@dataclass(frozen=True)
class RoleName(ValueObject[str]):
    value: str

    @override
    def _validate(self) -> None:
        if not self.value:
            raise WrongRoleNameError(self.value)
        if not ROLE_NAME_PATTERN.match(self.value):
            raise WrongRoleNameError(self.value)
