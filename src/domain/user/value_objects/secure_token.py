import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Self, override

from domain.common.value_object import BaseValueObject


@dataclass(frozen=True)
class SecureToken(BaseValueObject):
    value: str = ''
    created_at: datetime | None = None
    expires_at: datetime | None = None

    @override
    def _validate(self) -> None:
        pass

    @classmethod
    def create(cls, length: int = 32, expires_in_hours: int = 1) -> Self:
        now = datetime.now(UTC)
        return cls(
            value=secrets.token_urlsafe(length),
            created_at=now,
            expires_at=now + timedelta(hours=expires_in_hours),
        )

    @classmethod
    def create_hex(cls, length: int = 32, expires_in_hours: int = 1) -> Self:
        now = datetime.now(UTC)
        return cls(
            value=secrets.token_hex(length),
            created_at=now,
            expires_at=now + timedelta(hours=expires_in_hours),
        )

    def is_valid(self) -> bool:
        return self.expires_at is not None and datetime.now(UTC) < self.expires_at
