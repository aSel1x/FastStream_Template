from typing import Protocol


class UnitOfWorkInterface(Protocol):
    async def commit(self) -> None:
        """Commit transaction and publish domain events."""
        raise NotImplementedError

    async def rollback(self) -> None:
        """Rollback transaction."""
        raise NotImplementedError
