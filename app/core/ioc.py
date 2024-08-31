from collections.abc import AsyncIterable

from dishka import Provider, Scope, from_context, provide

from app.adapters import Adapters
from app.adapters.postgres import PostgresDB
from app.adapters.rabbitmq import AmqpQueue
from app.adapters.redis import RedisDB
from app.core.config import Config
from app.usecases import Services


class AppProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)
    adapter_amqp = from_context(provides=AmqpQueue, scope=Scope.APP)

    @provide(scope=Scope.APP)
    async def get_redis(self, config: Config) -> AsyncIterable[RedisDB]:
        async with Adapters.get_redis(config.redis_dsn) as redis:
            yield redis

    @provide(scope=Scope.REQUEST)
    async def get_postgres(self, config: Config) -> AsyncIterable[PostgresDB]:
        async with Adapters.get_postgres(config.pg_dsn) as postgres:
            yield postgres

    adapters = provide(
        Adapters,
        scope=Scope.REQUEST
    )

    services = provide(
        Services,
        scope=Scope.REQUEST
    )
