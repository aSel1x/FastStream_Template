from dataclasses import dataclass
from typing import ClassVar, override

from domain.common.exceptions import BaseDomainError
from domain.common.value_object import ValueObject

MIN_PASSWORD_LENGTH = 8
# bcrypt raises on inputs longer than 72 *bytes* rather than truncating them, so anything
# above this is a 500 at registration. Note that 36 Cyrillic characters already reach it.
MAX_PASSWORD_BYTES = 72


def _has_required_mix(value: str) -> bool:
    """Whether the password mixes cases, a digit and a symbol.

    Deliberately checked with Unicode-aware predicates rather than an `[A-Za-z\\d@$!%*?&]`
    allow-list. NIST SP 800-63B advises against composition rules that reject characters, and
    an allow-list silently rejects passphrases with spaces and every non-Latin script.
    """
    return (
        any(char.islower() for char in value)
        and any(char.isupper() for char in value)
        and any(char.isdigit() for char in value)
        and any(not char.isalnum() for char in value)
    )


@dataclass(eq=False)
class WrongPasswordValueError(BaseDomainError):
    status: ClassVar[int] = 400
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
        return f'Password must be at most {MAX_PASSWORD_BYTES} bytes long'


class PasswordTooWeakError(WrongPasswordValueError):
    @property
    @override
    def detail(self) -> str:
        return (
            'Password must contain at least one lowercase letter, one uppercase letter, '
            'one digit, and one non-alphanumeric character'
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
        if len(self.value.encode('utf-8')) > MAX_PASSWORD_BYTES:
            raise PasswordTooLongError(self.value)
        if not _has_required_mix(self.value):
            raise PasswordTooWeakError(self.value)


@dataclass(frozen=True)
class HashedPassword(ValueObject[bytes]):
    value: bytes

    @override
    def _validate(self) -> None:
        if not self.value or len(self.value) == 0:
            raise ValueError('Hashed password cannot be empty')
