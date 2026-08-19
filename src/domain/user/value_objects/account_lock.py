from typing import override
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from domain.common.value_object import BaseValueObject


@dataclass(frozen=True)
class AccountLockInfo(BaseValueObject):
    is_locked: bool = False
    locked_at: datetime | None = None
    lock_reason: str | None = None
    failed_attempts: int = 0
    lock_until: datetime | None = None

    @override
    def _validate(self) -> None:
        pass

    @classmethod
    def create(cls) -> 'AccountLockInfo':
        return cls()

    @classmethod
    def create_locked(cls, reason: str, until: datetime | None = None) -> 'AccountLockInfo':
        return cls(
            is_locked=True,
            locked_at=datetime.now(UTC),
            lock_reason=reason,
            lock_until=until,
        )

    def record_failed_attempt(self, max_attempts: int = 5, lockout_duration_minutes: int = 15) -> 'AccountLockInfo':
        new_failed_attempts = self.failed_attempts + 1
        is_locked = new_failed_attempts >= max_attempts
        lock_until: datetime | None = None
        if is_locked:
            lock_until = datetime.now(UTC) + timedelta(minutes=lockout_duration_minutes)
        return AccountLockInfo(
            is_locked=is_locked,
            locked_at=self.locked_at,
            lock_reason=self.lock_reason,
            failed_attempts=new_failed_attempts,
            lock_until=lock_until,
        )

    def record_successful_login(self) -> 'AccountLockInfo':
        return AccountLockInfo(
            is_locked=False,
            locked_at=None,
            lock_reason=None,
            failed_attempts=0,
            lock_until=None,
        )

    def unlock(self) -> 'AccountLockInfo':
        return AccountLockInfo(
            is_locked=False,
            locked_at=self.locked_at,
            lock_reason=None,
            failed_attempts=0,
            lock_until=None,
        )

    def is_locked_out(self) -> bool:
        if not self.is_locked:
            return False
        if self.lock_until and datetime.now(UTC) >= self.lock_until:
            return False
        return True
