import abc
from typing import Generic, TypeVar

from redis.asyncio import Redis
from sqlmodel import SQLModel

from app.models.base import IDModel

AbstractModel = TypeVar('AbstractModel', bound=SQLModel)
AbstractIDModel = TypeVar('AbstractIDModel', bound=IDModel)


class Repository(Generic[AbstractModel], metaclass=abc.ABCMeta):
    def __init__(self, model: type[AbstractModel], client: Redis):
        self.model = model
        self.client = client

    async def create(self, model: AbstractIDModel) -> bool | None:
        key = f"{self.model.__name__}:{model.id}"
        return await self.client.set(key, model.model_dump_json())

    async def retrieve_one(self, ident: int | str) -> AbstractModel | None:
        key = f"{self.model.__name__}:{ident}"
        if data := await self.client.get(key):
            return self.model.model_validate_json(data)
        return None

    async def retrieve_many(self) -> list[AbstractModel]:
        keys = await self.client.keys(f"{self.model.__name__}:*")
        values = await self.client.mget(keys)
        return [self.model.model_validate_json(data) for data in values if data]

    async def delete(self, ident: int | str) -> int:
        key = f"{self.model.__name__}:{ident}"
        return await self.client.delete(key)
