from typing import override

from application.common.interfaces.uow import UnitOfWorkInterface

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyUoW(UnitOfWorkInterface):
    _session: AsyncSession

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @override
    async def commit(self) -> None:
        try:
            await self._session.commit()
        except SQLAlchemyError:
            raise

    @override
    async def rollback(self) -> None:
        try:
            await self._session.rollback()
        except SQLAlchemyError:
            raise
