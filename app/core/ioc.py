from typing import AsyncIterable, Annotated

from fastapi import Depends as FromFastapi
from fastapi.security import APIKeyHeader
from dishka import Provider, Scope, provide, from_context
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import Config
from app.core.database import new_session_maker
from app.core.security import Security

from app.repositories import Repositories
from app.services import Services
from app.models import user


class AppProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)

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
