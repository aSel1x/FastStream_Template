import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Self, override

from domain.common.value_object import BaseValueObject


@dataclass(frozen=True)
class TwoFactorSecret(BaseValueObject):
    secret: str = ''
    backup_codes: tuple[str, ...] = field(default_factory=tuple)
    enabled_at: datetime | None = None

    @override
    def _validate(self) -> None:
        pass

    @classmethod
    def create(cls, secret: str) -> Self:
        backup_codes = tuple(secrets.token_hex(8) for _ in range(10))
        return cls(
            secret=secret,
            backup_codes=backup_codes,
            enabled_at=None,
        )

    def enable(self) -> 'TwoFactorSecret':
        return TwoFactorSecret(
            secret=self.secret,
            backup_codes=self.backup_codes,
            enabled_at=datetime.now(UTC),
        )

    def consume_backup_code(self, code: str) -> 'TwoFactorSecret | None':
        """Return a new secret with the matched code removed, or None if `code` doesn't match any."""
        for stored in self.backup_codes:
            if secrets.compare_digest(stored, code):
                return TwoFactorSecret(
                    secret=self.secret,
                    backup_codes=tuple(c for c in self.backup_codes if c != stored),
                    enabled_at=self.enabled_at,
                )
        return None

    def remaining_backup_codes(self) -> int:
        return len(self.backup_codes)
