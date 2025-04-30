import logging

from application.common.interfaces import UnitOfWorkInterface

logger = logging.getLogger(__name__)


class InMemoryUoW(UnitOfWorkInterface):
    """
    In-memory unit of work for testing purposes.
    """

    async def commit(self):
        logger.debug('Committing in-memory transaction (does nothing).')

    async def rollback(self):
        logger.debug('Rolling back in-memory transaction (does nothing).')
