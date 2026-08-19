import hashlib
from dataclasses import dataclass
from typing import Self, override

from domain.common.exceptions import BaseDomainError
from domain.common.value_object import ValueObject


@dataclass(eq=False)
class WrongTokenHashError(BaseDomainError):
    @property
    @override
    def detail(self) -> str:
        return 'Token hash cannot be empty'


@dataclass(frozen=True)
class TokenHash(ValueObject[bytes]):
    """Hash of an opaque high-entropy token (e.g. a refresh token) used for lookup-by-hash.

    Deliberately SHA-256, not a salted password hash like bcrypt: refresh tokens are already
    random and high-entropy, and the hash must be deterministic so a repository can look one up
    by exact equality.
    """

    value: bytes

    @override
    def _validate(self) -> None:
        if not self.value:
            raise WrongTokenHashError()

    @classmethod
    def from_raw(cls, raw_token: str) -> Self:
        return cls(hashlib.sha256(raw_token.encode()).digest())
