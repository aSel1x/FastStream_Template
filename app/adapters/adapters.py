from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

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
        async with AsyncExitStack() as stack:
            postgres = await stack.enter_async_context(PostgresDB(config.postgres.dsn))
            rabbit = await stack.enter_async_context(RabbitQueue(config.rabbit.dsn, config.redis.dsn))
            redis = await stack.enter_async_context(RedisDB(config.redis.dsn))

            yield cls(postgres, rabbit, redis)
