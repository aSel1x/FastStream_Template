from typing import ClassVar, final, override

from domain.common.exceptions import BaseAppError


class BaseApplicationError(BaseAppError):
    @property
    @override
    def detail(self) -> str:
        return 'An application error occurred'


@final
class ConfigurationError(BaseApplicationError):
    status: ClassVar[int] = 500

    def __init__(self, message: str) -> None:
        self._detail = message
        super().__init__()

    @property
    @override
    def detail(self) -> str:
        return self._detail


class TooManyLoginAttemptsError(BaseApplicationError):
    status: ClassVar[int] = 429

    @property
    @override
    def detail(self) -> str:
        return 'Too many login attempts, try again later'


@final
class OAuthClientNotFoundError(BaseApplicationError):
    status: ClassVar[int] = 404

    def __init__(self, client_id: str) -> None:
        self._client_id = client_id
        super().__init__()

    @property
    @override
    def detail(self) -> str:
        return f'OAuth client "{self._client_id}" not found'
