import asyncio
from typing import AsyncGenerator, Any

import pytest

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from app.core.config import Config
from app.usecases import Services
from app.adapters import Adapters
from app.adapters.postgres import PostgresDB
from app.adapters.rabbitmq import AmqpQueue
from app.adapters.redis import RedisDB


@pytest.fixture(scope="session", autouse=True)
def config(event_loop) -> Config:
    return Config()


@pytest.fixture(scope="session", autouse=True)
async def postgres(config: Config, event_loop) -> AsyncGenerator[PostgresDB, None]:
    engine = create_async_engine(config.postgres.dsn.unicode_string(), poolclass=NullPool)
    async with PostgresDB(config.postgres.dsn, engine=engine) as postgres:
        async with engine.begin() as con:
            await con.run_sync(SQLModel.metadata.create_all)
        yield postgres
        async with engine.begin() as con:
            await con.run_sync(SQLModel.metadata.drop_all)


@pytest.fixture(scope="session", autouse=True)
async def rabbit(config: Config, event_loop) -> AsyncGenerator[AmqpQueue, None]:
    async with AmqpQueue(config.rabbit.dsn) as rabbit:
        yield rabbit
        await rabbit.broker.close()


@pytest.fixture(scope="session", autouse=True)
async def redis(config: Config, event_loop) -> AsyncGenerator[RedisDB, None]:
    async with RedisDB(config.redis.dsn) as redis:
        yield redis
        await redis._RedisDB__client.flushdb()
        await redis._RedisDB__client.aclose()


@pytest.fixture(scope="function", autouse=True)
async def adapters(postgres: PostgresDB, rabbit: AmqpQueue, redis: RedisDB) -> Adapters:
    return Adapters(postgres=postgres, rabbit=rabbit, redis=redis)


@pytest.fixture(scope="function", autouse=True)
async def service(adapters: Adapters, config: Config) -> Services:
    return Services(adapters=adapters, config=config)


@pytest.fixture(scope="module", autouse=True)
def cache() -> dict[str, Any]:
    cache = dict()
    yield cache
    cache.clear()


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()
