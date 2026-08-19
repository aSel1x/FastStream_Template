from typing import override
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from domain.common.value_object import BaseValueObject


@dataclass(frozen=True)
class PasswordResetToken(BaseValueObject):
    token: str = ''
    created_at: datetime | None = None
    expires_at: datetime | None = None
    is_used: bool = False

    @override
    def _validate(self) -> None:
        pass

    @classmethod
    def create(cls, token: str, expires_in_hours: int = 1) -> 'PasswordResetToken':
        now = datetime.now(UTC)
        return cls(
            token=token,
            created_at=now,
            expires_at=now + timedelta(hours=expires_in_hours),
            is_used=False,
        )

    def is_valid(self) -> bool:
        return (
            not self.is_used
            and self.expires_at is not None
            and datetime.now(UTC) < self.expires_at
        )

    def mark_used(self) -> 'PasswordResetToken':
        return PasswordResetToken(
            token=self.token,
            created_at=self.created_at,
            expires_at=self.expires_at,
            is_used=True,
        )
