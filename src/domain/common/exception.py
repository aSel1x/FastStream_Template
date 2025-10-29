from dataclasses import dataclass
from typing import ClassVar, override

# pyright: reportUnsafeMultipleInheritance=false


@dataclass(eq=False)
class BaseAppError(Exception):
    status: ClassVar[int] = 500

    @property
    def detail(self) -> str:
        return 'An app error occurred'


class BaseDomainError(BaseAppError):
    @property
    @override
    def detail(self) -> str:
        return 'A domain error occurred'
