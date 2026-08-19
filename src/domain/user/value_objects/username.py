import re
from dataclasses import dataclass
from typing import override

from domain.common.exceptions import BaseDomainError
from domain.common.value_object import ValueObject

MAX_USERNAME_LENGTH = 32
USERNAME_PATTERN = re.compile(r'^[A-Za-z][A-Za-z0-9_]+$')


@dataclass(eq=False)
class WrongUsernameValueError(BaseDomainError):
    username: str


class EmptyUsernameError(WrongUsernameValueError):
    @property
    @override
    def detail(self) -> str:
        return "Username can't be empty"


class TooLongUsernameError(WrongUsernameValueError):
    @property
    @override
    def detail(self) -> str:
        return f'Too long username "{self.username}"'


class WrongUsernameFormatError(WrongUsernameValueError):
    @property
    @override
    def detail(self) -> str:
        return f'Wrong username format "{self.username}"'


@dataclass(frozen=True)
class Username(ValueObject[str]):
    value: str

    @override
    def _validate(self) -> None:
        if len(self.value) == 0:
            raise EmptyUsernameError(self.value)
        if len(self.value) > MAX_USERNAME_LENGTH:
            raise TooLongUsernameError(self.value)
        if not USERNAME_PATTERN.match(self.value):
            raise WrongUsernameFormatError(self.value)
