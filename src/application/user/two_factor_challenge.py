"""The short-lived handle that stands between a correct password and a session.

When an account has a second factor, a correct password alone must not yield anything the
caller can use. It yields this instead: an opaque token that only becomes a session once the
second factor is verified.

Both entry points share it — the browser flow through Hydra's login bridge and the direct
JSON API — so the two cannot drift apart on whether 2FA is actually enforced.

Storage is a port: how a challenge is serialised, and where it is kept, is infrastructure.
"""

from dataclasses import dataclass
from typing import ClassVar, Protocol, final, override
from uuid import UUID

from application.common.exceptions import BaseApplicationError
from domain.user.entities.session import DeviceInfo

CHALLENGE_TTL_SECONDS = 300
MAX_ATTEMPTS = 5


@final
class TwoFactorChallengeExpiredError(BaseApplicationError):
    """The pending challenge is gone: it expired, was used, or ran out of attempts."""

    status: ClassVar[int] = 401

    @property
    @override
    def detail(self) -> str:
        return 'Two-factor challenge expired; sign in again'


@dataclass(frozen=True)
class TwoFactorChallenge:
    user_id: UUID
    device_info: DeviceInfo
    attempts: int = 0
    #: Carried through for the Hydra bridge, which has to resume the login it interrupted.
    login_challenge: str | None = None

    def with_failed_attempt(self) -> TwoFactorChallenge:
        return TwoFactorChallenge(
            user_id=self.user_id,
            device_info=self.device_info,
            attempts=self.attempts + 1,
            login_challenge=self.login_challenge,
        )

    def is_exhausted(self) -> bool:
        """Whether too many wrong codes have been tried.

        Bounded per challenge, not only per IP: a six-digit code is guessable in far fewer
        tries than a generic per-IP request limit allows.
        """
        return self.attempts >= MAX_ATTEMPTS


class TwoFactorChallengeStore(Protocol):
    async def issue(self, challenge: TwoFactorChallenge) -> str:
        """Store a challenge and return the opaque token that names it."""
        ...

    async def read(self, token: str) -> TwoFactorChallenge:
        """Return the challenge, or raise `TwoFactorChallengeExpiredError`."""
        ...

    async def record_failure(self, token: str, challenge: TwoFactorChallenge) -> None:
        """Count a wrong code; discard the challenge and raise once it is exhausted."""
        ...

    async def discard(self, token: str) -> None:
        """Retire a challenge. Idempotent."""
        ...
