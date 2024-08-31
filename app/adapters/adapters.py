from contextlib import asynccontextmanager

from pydantic import AmqpDsn, PostgresDsn, RedisDsn

from .postgres import PostgresDB
from .rabbitmq import AmqpQueue
from .redis import RedisDB


class Adapters:
    def __init__(
            self,
            postgres: PostgresDB,
            redis: RedisDB,
            amqp: AmqpQueue,
    ) -> None:
        self.postgres = postgres
        self.redis = redis
        self.amqp = amqp

    @staticmethod
    @asynccontextmanager
    async def get_redis(redis_dsn: RedisDsn):
        async with RedisDB(redis_dsn) as redis:
            yield redis

    @staticmethod
    @asynccontextmanager
    async def get_rabbitmq(amqp_dsn: AmqpDsn):
        async with AmqpQueue(amqp_dsn) as amqp:
            yield amqp

    @staticmethod
    @asynccontextmanager
    async def get_postgres(postgres_dsn: PostgresDsn):
        async with PostgresDB(postgres_dsn) as postgres:
            yield postgres
