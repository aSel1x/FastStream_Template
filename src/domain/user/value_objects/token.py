# pyright: reportUnsafeMultipleInheritance = false

import datetime as dt
from dataclasses import dataclass
from enum import Enum
from typing import override

from domain.common.exceptions import BaseDomainError
from domain.common.value_object import ValueObject


class TokenType(Enum):
    ACCESS = 'access'
    REFRESH = 'refresh'


@dataclass(eq=False)
class WrongTokenValueError(ValueError, BaseDomainError):
    token: str

    @property
    @override
    def detail(self) -> str:
        return 'Invalid token'


class EmptyTokenError(WrongTokenValueError):
    @property
    @override
    def detail(self) -> str:
        return "Token can't be empty"


@dataclass(frozen=True)
class Token(ValueObject[str]):
    value: str

    @override
    def _validate(self) -> None:
        if not self.value or len(self.value) == 0:
            raise EmptyTokenError(self.value)


@dataclass(frozen=True)
class ExpiresAt(ValueObject[dt.datetime]):
    value: dt.datetime

    @override
    def _validate(self) -> None:
        if self.value <= dt.datetime.now(dt.timezone.utc):
            raise ValueError('ExpiresAt must be in the future')

    def is_expired(self) -> bool:
        return dt.datetime.now(dt.timezone.utc) >= self.value


@dataclass(frozen=True)
class TokenResponse(ValueObject[dict[str, object]]):
    access_token: Token
    refresh_token: Token
    access_token_expires_at: ExpiresAt
    refresh_token_expires_at: ExpiresAt
    token_type: TokenType = TokenType.ACCESS

    @override
    def _validate(self) -> None:
        pass

    def to_dict(self) -> dict[str, object]:
        return {
            'access_token': self.access_token.value,
            'refresh_token': self.refresh_token.value,
            'access_token_expires_at': self.access_token_expires_at.value.isoformat(),
            'refresh_token_expires_at': self.refresh_token_expires_at.value.isoformat(),
            'token_type': self.token_type.value,
        }
