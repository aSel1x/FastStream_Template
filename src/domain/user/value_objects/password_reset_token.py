from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from secrets import compare_digest
from typing import override

from domain.common.value_object import BaseValueObject
from domain.user.value_objects.token_hash import TokenHash


@dataclass(frozen=True)
class PasswordResetToken(BaseValueObject):
    """A pending password reset.

    Stores the SHA-256 of the emailed token, never the token itself: anything that can read
    the users table would otherwise be able to take over every account with a live reset.
    """

    token_hash: TokenHash
    created_at: datetime | None = None
    expires_at: datetime | None = None
    is_used: bool = False

    @override
    def _validate(self) -> None:
        pass

    @classmethod
    def create(cls, token: str, expires_in_hours: int = 1) -> PasswordResetToken:
        now = datetime.now(UTC)
        return cls(
            token_hash=TokenHash.from_raw(token),
            created_at=now,
            expires_at=now + timedelta(hours=expires_in_hours),
            is_used=False,
        )

    def is_valid(self) -> bool:
        return (
            not self.is_used and self.expires_at is not None and datetime.now(UTC) < self.expires_at
        )

    def matches(self, token: str) -> bool:
        return compare_digest(self.token_hash.to_raw(), TokenHash.from_raw(token).to_raw())

    def mark_used(self) -> PasswordResetToken:
        return replace(self, is_used=True)
