from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .config import SQLAlchemyConfig


@asynccontextmanager
async def build_sa_engine(
    sqlalchemy_config: SQLAlchemyConfig,
) -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(
        sqlalchemy_config.full_url,
        echo=True,
        echo_pool=sqlalchemy_config.echo,
        pool_size=50,
    )
    yield engine

    await engine.dispose()


def build_sa_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    session_factory = async_sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    return session_factory
