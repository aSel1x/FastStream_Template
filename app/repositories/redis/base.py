import abc
from typing import Generic, TypeVar

from sqlmodel import SQLModel
from redis.asyncio import Redis

from app.models.base import IDModel

AbstractModel = TypeVar('AbstractModel', bound=SQLModel)
AbstractIDModel = TypeVar('AbstractIDModel', bound=IDModel)


class Repository(Generic[AbstractModel], metaclass=abc.ABCMeta):
    def __init__(self, model: type[AbstractModel], client: Redis):
        self.model = model
        self.client = client

    async def create(self, model: AbstractIDModel) -> AbstractIDModel:
        key = f"{self.model.__name__}:{model.id}"
        await self.client.set(key, model.model_dump_json())
        return model

    async def retrieve_one(self, ident: int | str = None) -> AbstractModel | None:
        key = f"{self.model.__name__}:{ident}"
        if data := await self.client.get(key):
            return self.model.model_validate_json(data)

    async def retrieve_many(self) -> list[AbstractModel]:
        keys = await self.client.keys(f"{self.model.__name__}:*")
        values = await self.client.mget(keys)
        return [self.model.model_validate_json(data) for data in values]

    async def delete(self, ident: int | str) -> None:
        key = f"{self.model.__name__}:{ident}"
        await self.client.delete(key)
