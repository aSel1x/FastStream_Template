from domain.common import AppError


class BaseApplicationError(AppError):
    @property
    def detail(self) -> str:
        return 'An application error occurred'
