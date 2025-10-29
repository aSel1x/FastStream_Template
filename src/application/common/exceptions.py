from typing import override

from domain.common.exception import BaseAppError


class BaseApplicationError(BaseAppError):
    @property
    @override
    def detail(self) -> str:
        return 'An application error occurred'
