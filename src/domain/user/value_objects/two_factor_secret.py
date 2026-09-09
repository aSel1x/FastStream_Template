import secrets
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Self, override

from domain.common.value_object import BaseValueObject
from domain.user.value_objects.token_hash import TokenHash

BACKUP_CODE_COUNT = 10
BACKUP_CODE_BYTES = 8


@dataclass(frozen=True)
class TwoFactorSecret(BaseValueObject):
    """TOTP enrolment state.

    `secret` is the TOTP seed and has to stay recoverable, so the repository encrypts it at
    rest. Backup codes are one-shot credentials that only ever need to be *checked*, so only
    their hashes are kept — the plaintext exists once, in the response to enrolment.
    """

    secret: str = ''
    backup_code_hashes: tuple[TokenHash, ...] = field(default_factory=tuple)
    enabled_at: datetime | None = None

    @override
    def _validate(self) -> None:
        pass

    @classmethod
    def create(cls, secret: str) -> tuple[Self, tuple[str, ...]]:
        """Return the new enrolment and the plaintext backup codes to show the user once."""
        codes = tuple(secrets.token_hex(BACKUP_CODE_BYTES) for _ in range(BACKUP_CODE_COUNT))
        return (
            cls(
                secret=secret,
                backup_code_hashes=tuple(TokenHash.from_raw(code) for code in codes),
                enabled_at=None,
            ),
            codes,
        )

    def enable(self) -> TwoFactorSecret:
        return replace(self, enabled_at=datetime.now(UTC))

    def consume_backup_code(self, code: str) -> TwoFactorSecret | None:
        """Return a new secret without the matched code, or None if nothing matched."""
        candidate = TokenHash.from_raw(code)
        for stored in self.backup_code_hashes:
            if secrets.compare_digest(stored.to_raw(), candidate.to_raw()):
                return replace(
                    self,
                    backup_code_hashes=tuple(
                        held for held in self.backup_code_hashes if held != stored
                    ),
                )
        return None

    def remaining_backup_codes(self) -> int:
        return len(self.backup_code_hashes)
