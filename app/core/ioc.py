
from typing import AsyncIterable
from dishka import Provider, Scope, from_context, provide

from app.core.config import Config
from app.adapters import Database
from app.repositories import Repositories
from app.usecases import Services


class AppProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)

    @provide(scope=Scope.REQUEST)
    async def get_db(self, config: Config) -> AsyncIterable['Database']:
        async with Database(config.pg_dsn) as db:
            yield db

    services = provide(
        Services,
        scope=Scope.REQUEST,
    )
