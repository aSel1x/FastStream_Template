import re
from dataclasses import dataclass
from typing import override

from domain.common.exceptions import BaseDomainError
from domain.common.value_object import ValueObject

EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


@dataclass(eq=False)
class WrongEmailValueError(BaseDomainError):
    email: str

    @property
    @override
    def detail(self) -> str:
        return 'Invalid email'


class EmptyEmailError(WrongEmailValueError):
    @property
    @override
    def detail(self) -> str:
        return "Email can't be empty"


class InvalidEmailFormatError(WrongEmailValueError):
    @property
    @override
    def detail(self) -> str:
        return f'Invalid email format "{self.email}"'


@dataclass(frozen=True)
class Email(ValueObject[str | None]):
    value: str | None

    @override
    def _validate(self) -> None:
        if self.value is None:
            return
        if not self.value:
            raise EmptyEmailError(self.value)
        if not EMAIL_PATTERN.match(self.value):
            raise InvalidEmailFormatError(self.value)
