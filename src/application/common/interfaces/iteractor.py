from typing import Generic, Protocol, TypeVar

Input = TypeVar('Input', contravariant=True)
Output = TypeVar('Output', covariant=True)


class InteractorInterface(Generic[Input, Output], Protocol):
    async def __call__(self, input: Input) -> Output:
        raise NotImplementedError
