from typing import Protocol
from uuid import UUID


class UUIDGeneratorInterface(Protocol):
    def __call__(self) -> UUID:
        raise NotImplementedError
