from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import override


@dataclass(frozen=True)
class BaseEntity(ABC):
    """Entities compare by identity, not by value — override `_identity()` to say what identifies one."""

    @abstractmethod
    def _identity(self) -> object: ...

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseEntity) or type(other) is not type(self):
            return NotImplemented
        return self._identity() == other._identity()

    @override
    def __hash__(self) -> int:
        return hash((type(self), self._identity()))