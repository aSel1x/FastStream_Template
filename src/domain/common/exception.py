from dataclasses import dataclass
from typing import ClassVar


@dataclass(eq=False)
class BaseAppError(Exception):
    status: ClassVar[int] = 500

    @property
    def detail(self) -> str:
        return 'An app error occurred'


class BaseDomainError(BaseAppError):
    @property
    def detail(self) -> str:
        return 'A domain error occurred'
