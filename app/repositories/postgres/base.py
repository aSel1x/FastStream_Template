import abc
from collections.abc import Sequence
from typing import Generic, TypeVar

import sqlmodel as sm
from sqlalchemy.ext.asyncio import async_sessionmaker

AbstractModel = TypeVar('AbstractModel', bound=sm.SQLModel)


class Repository(Generic[AbstractModel], metaclass=abc.ABCMeta):
    def __init__(self, model: type[AbstractModel], session_maker: async_sessionmaker):
        self.model = model
        self.session = session_maker

    async def create(self, model: AbstractModel) -> AbstractModel:
        async with self.session.begin() as session:
            model = self.model.model_validate(model)
            session.add(model)
            await session.flush()
            return model

    async def retrieve_one(
            self,
            ident: int | None = None,
            where_clauses: list[bool] | None = None,
    ) -> AbstractModel | None:
        async with self.session.begin() as session:
            if ident is not None:
                return await session.get(self.model, ident)
            stmt = sm.select(self.model)
            if where_clauses is not None:
                stmt = stmt.where(sm.and_(*where_clauses))
            entity = await session.exec(stmt)
            return entity.first()

    async def retrieve_many(
            self,
            where_clauses: list[bool] | None = None,
            limit: int | None = None,
            order_by: sm.Column | None = None
    ) -> Sequence[AbstractModel] | None:
        async with self.session.begin() as session:
            stmt = sm.select(self.model)
            if where_clauses is not None:
                stmt = stmt.where(sm.and_(*where_clauses))
            if limit is not None:
                stmt = stmt.limit(limit)
            if order_by is not None:
                stmt = stmt.order_by(order_by)
            entity = await session.exec(stmt)
            return entity.all()

    async def delete(self, instance: AbstractModel) -> None:
        async with self.session.begin() as session:
            await session.delete(instance)
            await session.flush()
