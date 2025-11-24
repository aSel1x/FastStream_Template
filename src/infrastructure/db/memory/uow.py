import logging
from typing import override

from application.common.interfaces.uow import UnitOfWorkInterface

logger = logging.getLogger(__name__)


class InMemoryUoW(UnitOfWorkInterface):
    @override
    async def commit(self) -> None:
        logger.debug('Committing in-memory transaction (does nothing).')

    @override
    async def rollback(self) -> None:
        logger.debug('Rolling back in-memory transaction (does nothing).')
