from typing import AsyncGenerator, AsyncIterable

from dishka import Provider, Scope, from_context, provide
from fastapi import FastAPI
from faststream.rabbit import RabbitBroker
from taskiq_faststream import AppWrapper, StreamScheduler
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.broker import new_broker
from app.core.config import Config
from app.core.database import new_session_maker
from app.core.security import Security
from app.repositories import Repositories
from app.services import Services


class AppProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)
    fastapi_app = from_context(provides=Config, scope=Scope.APP)
    taskiq_faststream = from_context(provides=AppWrapper, scope=Scope.APP)
    taskiq_faststream_scheduler = from_context(provides=StreamScheduler, scope=Scope.APP)

    @provide(scope=Scope.APP)
    def get_session_maker(self, config: Config) -> async_sessionmaker[AsyncSession]:
        return new_session_maker(config.pg_dsn)

    @provide(scope=Scope.REQUEST)
    async def get_session(self, session_maker: async_sessionmaker[AsyncSession]) -> AsyncIterable[AsyncSession]:
        async with session_maker() as session:
            yield session

    repositories = provide(
        Repositories,
        scope=Scope.REQUEST,
    )

    services = provide(
        Services,
        scope=Scope.REQUEST,
    )

    @provide(scope=Scope.APP)
    def get_security(self, config: Config) -> Security:
        return Security(config)
