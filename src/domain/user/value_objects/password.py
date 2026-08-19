import re
from dataclasses import dataclass
from typing import override

from domain.common.exceptions import BaseDomainError
from domain.common.value_object import ValueObject

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128
PASSWORD_PATTERN = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$'
)


@dataclass(eq=False)
class WrongPasswordValueError(BaseDomainError):
    password: str

    @property
    @override
    def detail(self) -> str:
        return 'Invalid password'


class EmptyPasswordError(WrongPasswordValueError):
    @property
    @override
    def detail(self) -> str:
        return "Password can't be empty"


class PasswordTooShortError(WrongPasswordValueError):
    @property
    @override
    def detail(self) -> str:
        return f'Password must be at least {MIN_PASSWORD_LENGTH} characters long'


class PasswordTooLongError(WrongPasswordValueError):
    @property
    @override
    def detail(self) -> str:
        return f'Password must be at most {MAX_PASSWORD_LENGTH} characters long'


class PasswordTooWeakError(WrongPasswordValueError):
    @property
    @override
    def detail(self) -> str:
        return (
            'Password must contain at least one lowercase letter, '
            'one uppercase letter, one digit, and one special character (@$!%*?&)'
        )


@dataclass(frozen=True)
class PlainPassword(ValueObject[str]):
    value: str

    @override
    def _validate(self) -> None:
        if not self.value:
            raise EmptyPasswordError(self.value)
        if len(self.value) < MIN_PASSWORD_LENGTH:
            raise PasswordTooShortError(self.value)
        if len(self.value) > MAX_PASSWORD_LENGTH:
            raise PasswordTooLongError(self.value)
        if not PASSWORD_PATTERN.match(self.value):
            raise PasswordTooWeakError(self.value)


@dataclass(frozen=True)
class HashedPassword(ValueObject[bytes]):
    value: bytes

    @override
    def _validate(self) -> None:
        if not self.value or len(self.value) == 0:
            raise ValueError('Hashed password cannot be empty')
