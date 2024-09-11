from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.core.config import Config

from .postgres import PostgresDB
from .rabbitmq import RabbitQueue
from .redis import RedisDB


class Adapters:
    def __init__(
            self,
            postgres: PostgresDB,
            rabbit: RabbitQueue,
            redis: RedisDB,
    ) -> None:
        self.postgres = postgres
        self.rabbit = rabbit
        self.redis = redis

    @classmethod
    @asynccontextmanager
    async def create(cls, config: Config) -> AsyncIterator['Adapters']:
        async with PostgresDB(config.postgres.dsn) as postgres:
            async with RabbitQueue(config.rabbit.dsn, config.redis.dsn) as rabbit:
                async with RedisDB(config.redis.dsn) as redis:
                    yield cls(postgres, rabbit, redis)
