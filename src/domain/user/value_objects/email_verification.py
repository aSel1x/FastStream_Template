from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import compare_digest
from typing import override

from domain.common.value_object import BaseValueObject
from domain.user.value_objects.token_hash import TokenHash


@dataclass(frozen=True)
class EmailVerification(BaseValueObject):
    """Email-verification state.

    Stores the SHA-256 of the emailed token, never the token itself: a read of the users table
    otherwise hands over a working verification link for every unverified account.
    """

    is_verified: bool = False
    token_hash: TokenHash | None = None
    verified_at: datetime | None = None
    expires_at: datetime | None = None

    @override
    def _validate(self) -> None:
        pass

    @classmethod
    def create_unverified(cls, token: str, expires_in_hours: int = 24) -> EmailVerification:
        return cls(
            is_verified=False,
            token_hash=TokenHash.from_raw(token),
            verified_at=None,
            expires_at=datetime.now(UTC) + timedelta(hours=expires_in_hours),
        )

    def verify(self, token: str) -> bool:
        if self.is_verified:
            return True
        if self.token_hash is None:
            return False
        if not compare_digest(self.token_hash.to_raw(), TokenHash.from_raw(token).to_raw()):
            return False
        return not (self.expires_at and datetime.now(UTC) >= self.expires_at)

    def mark_verified(self) -> EmailVerification:
        return EmailVerification(
            is_verified=True,
            token_hash=None,
            verified_at=datetime.now(UTC),
            expires_at=None,
        )
