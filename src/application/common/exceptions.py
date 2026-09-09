from dataclasses import dataclass
from typing import ClassVar, final, override

from domain.common.exceptions import BaseAppError


class BaseApplicationError(BaseAppError):
    @property
    @override
    def detail(self) -> str:
        return 'An application error occurred'


@final
@dataclass(eq=False)
class ConfigurationError(BaseApplicationError):
    """The service is misconfigured. Raised at startup so it fails fast, not at first use."""

    status: ClassVar[int] = 500
    message: str = ''

    @property
    @override
    def detail(self) -> str:
        return self.message or 'The service is misconfigured'


@final
@dataclass(eq=False)
class TooManyLoginAttemptsError(BaseApplicationError):
    status: ClassVar[int] = 429
    #: Seconds until the caller may try again, surfaced as the Retry-After header.
    retry_after_seconds: int | None = None

    @property
    @override
    def detail(self) -> str:
        return 'Too many login attempts, try again later'


@final
@dataclass(eq=False)
class OAuthClientNotFoundError(BaseApplicationError):
    status: ClassVar[int] = 404
    client_id: str = ''

    @property
    @override
    def detail(self) -> str:
        return f'OAuth client "{self.client_id}" not found'
