from dataclasses import dataclass
from typing import ClassVar, override


@dataclass(eq=False)
class BaseAppError(Exception):
    """Base application error.

    `detail` is mirrored into `args` so `str(exc)`, `repr(exc)`, tracebacks, logging and
    pickling all show the message. With the message living only in a property, every one of
    those rendered an empty exception.
    """

    status: ClassVar[int] = 500

    def __post_init__(self) -> None:
        super().__init__(self.detail)

    @property
    def detail(self) -> str:
        return 'An app error occurred'


class BaseDomainError(BaseAppError):
    @property
    @override
    def detail(self) -> str:
        return 'A domain error occurred'
