from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.core.config import Config
from .postgres import PostgresDB
from .rabbitmq import AmqpQueue
from .redis import RedisDB


class Adapters:
    def __init__(
            self,
            postgres: PostgresDB,
            rabbit: AmqpQueue,
            redis: RedisDB,
    ) -> None:
        self.postgres = postgres
        self.rabbit = rabbit
        self.redis = redis

    @classmethod
    @asynccontextmanager
    async def create(cls, config: Config) -> AsyncGenerator['Adapters', None]:
        async with PostgresDB(config.postgres.dsn) as postgres:
            async with AmqpQueue(config.rabbit.dsn) as rabbit:
                async with RedisDB(config.redis.dsn) as redis:
                    yield cls(postgres, rabbit, redis)
