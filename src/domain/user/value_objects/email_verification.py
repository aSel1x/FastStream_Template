from typing import override
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from domain.common.value_object import BaseValueObject


@dataclass(frozen=True)
class EmailVerification(BaseValueObject):
    is_verified: bool = False
    verification_token: str | None = None
    verified_at: datetime | None = None
    expires_at: datetime | None = None

    @override
    def _validate(self) -> None:
        pass

    @classmethod
    def create_unverified(cls, token: str, expires_in_hours: int = 24) -> 'EmailVerification':
        return cls(
            is_verified=False,
            verification_token=token,
            verified_at=None,
            expires_at=datetime.now(UTC) + timedelta(hours=expires_in_hours),
        )

    def verify(self, token: str) -> bool:
        if self.is_verified:
            return True
        if self.verification_token != token:
            return False
        if self.expires_at and datetime.now(UTC) >= self.expires_at:
            return False
        return True

    def mark_verified(self) -> 'EmailVerification':
        return EmailVerification(
            is_verified=True,
            verification_token=None,
            verified_at=datetime.now(UTC),
            expires_at=None,
        )
