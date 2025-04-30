from abc import abstractmethod
from typing import Generic, Protocol, TypeVar

Input = TypeVar('Input')
Output = TypeVar('Output')


class InteractorInterface(Generic[Input, Output], Protocol):
    @abstractmethod
    async def __call__(self, input: Input) -> Output:
        pass
