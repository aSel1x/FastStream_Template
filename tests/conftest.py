from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import pytest_asyncio
from dishka import Provider, Scope, from_context, make_async_container, provide
from dishka.integrations import fastapi as fastapi_integration
from dishka.integrations import faststream as faststream_integration
from dishka.integrations import taskiq as taskiq_integration
from faststream.rabbit.testing import TestRabbitBroker
from faststream.testing import TestApp
from httpx import ASGITransport, AsyncClient
from redis.asyncio.client import Redis
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from taskiq import InMemoryBroker, TaskiqScheduler

from app.adapters import Adapters
from app.adapters.postgres import PostgresDB
from app.adapters.rabbitmq import RabbitQueue
from app.adapters.redis import RedisDB
from app.core.config import Config
from app.fastapi import FastAPIApp
from app.faststream import FastStreamApp
from app.taskiq import TaskIqApp
from app.usecases import Services

from .taskiq_faststream_testing import TestScheduleSource


@pytest.fixture(scope='session', autouse=True)
def config() -> Config:
    return Config()


@pytest.fixture(scope='session', autouse=True)
def postgres_engine(config: Config) -> AsyncEngine:
    return create_async_engine(config.postgres.dsn.unicode_string(), poolclass=NullPool)


@pytest.fixture(scope='session', autouse=True)
def redis_client(config: Config) -> Redis:
    return Redis.from_url(config.redis.dsn.unicode_string())


@pytest_asyncio.fixture(scope='module', loop_scope='session', autouse=True)
async def postgres_reset(postgres_engine: AsyncEngine) -> AsyncIterator[None]:
    async with postgres_engine.begin() as con:
        await con.run_sync(SQLModel.metadata.create_all)
    yield
    async with postgres_engine.begin() as con:
        await con.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture(scope='module', loop_scope='session', autouse=True)
async def redis_reset(redis_client: Redis) -> None:
    await redis_client.flushdb()
    await redis_client.aclose()  # type: ignore[attr-defined]


class TestAppProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)
    adapters = from_context(provides=Adapters, scope=Scope.APP)

    services = provide(
        Services,
        scope=Scope.REQUEST
    )


@pytest_asyncio.fixture(loop_scope='session', autouse=True)
async def container(
        config: Config,
        faststream_app: FastStreamApp,
        fastapi_app: FastAPIApp,
        taskiq_app: TaskIqApp,
        adapters: Adapters,
):
    container = make_async_container(
        TestAppProvider(),
        context={
            Config: config,
            FastStreamApp: faststream_app,
            FastAPIApp: fastapi_app,
            TaskIqApp: taskiq_app,
            Adapters: adapters,
        }
    )
    faststream_integration.setup_dishka(container, faststream_app.app)
    fastapi_integration.setup_dishka(container, fastapi_app.app)
    taskiq_integration.setup_dishka(container, taskiq_app.broker)
    yield container
    await container.close()


@pytest_asyncio.fixture(loop_scope='session', autouse=True)
async def http_client(config: Config, fastapi_app: FastAPIApp) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(fastapi_app.app),
                           base_url='http://0.0.0.0:8000/api/v1') as http_client:
        yield http_client


@pytest_asyncio.fixture(loop_scope='session', autouse=True)
async def fastapi_app(config: Config) -> AsyncIterator[FastAPIApp]:
    fastapi_app = FastAPIApp(config).initialize()
    yield fastapi_app


@pytest_asyncio.fixture(loop_scope='session', autouse=True)
async def faststream_app(config: Config) -> AsyncIterator[FastStreamApp]:
    faststream_app = FastStreamApp(config).initialize()
    async with TestRabbitBroker(faststream_app.broker) as br:
        async with TestApp(faststream_app.app) as app:
            faststream_app.broker = br
            faststream_app.app = app
            await faststream_app.app.start()
            yield faststream_app
            await faststream_app.app.stop()


@pytest_asyncio.fixture(loop_scope='session', autouse=True)
async def taskiq_app(config: Config, faststream_app: FastStreamApp) -> AsyncIterator[TaskIqApp]:
    taskiq_app = TaskIqApp(config)
    taskiq_app.broker = InMemoryBroker()
    taskiq_scheduler_source = TestScheduleSource(faststream_app.broker)
    taskiq_app.scheduler = TaskiqScheduler(taskiq_app.broker, [taskiq_scheduler_source])
    await taskiq_app.broker.startup()
    await taskiq_app.scheduler.startup()
    yield taskiq_app
    await taskiq_app.broker.shutdown()
    await taskiq_app.scheduler.shutdown()


@pytest_asyncio.fixture(loop_scope='session', autouse=True)
async def postgres(config: Config, postgres_engine: AsyncEngine) -> AsyncIterator[PostgresDB]:
    async with PostgresDB(config.postgres.dsn, engine=postgres_engine) as postgres:
        yield postgres


@pytest_asyncio.fixture(loop_scope='session', autouse=True)
async def rabbit(config: Config, faststream_app: FastStreamApp, taskiq_app: TaskIqApp) -> AsyncIterator[RabbitQueue]:
    async with RabbitQueue(
            rabbit_dsn=config.rabbit.dsn,
            redis_dsn=config.redis.dsn,
            faststream_broker=faststream_app.broker,
            faststream_app=faststream_app.app,
            taskiq_broker=taskiq_app.broker,
            taskiq_scheduler_source=taskiq_app.scheduler.sources[0],
            taskiq_scheduler=taskiq_app.scheduler,
    ) as rabbit:
        yield rabbit


@pytest_asyncio.fixture(loop_scope='session', autouse=True)
async def redis(config: Config, redis_client: Redis) -> AsyncIterator[RedisDB]:
    async with RedisDB(config.redis.dsn, client=redis_client) as redis:
        yield redis


@pytest_asyncio.fixture(loop_scope='session', autouse=True)
async def adapters(
        config: Config, postgres: PostgresDB, rabbit: RabbitQueue, redis: RedisDB
) -> Adapters:
    return Adapters(postgres, rabbit, redis)


@pytest_asyncio.fixture(loop_scope='session', autouse=True)
async def use_cases(adapters: Adapters, config: Config) -> Services:
    return Services(adapters, config)


@pytest_asyncio.fixture(scope='module', autouse=True)
def cache() -> Iterator[dict[str, Any]]:
    cache: dict[str, Any] = dict()
    yield cache
    cache.clear()


@pytest_asyncio.fixture
def anyio_backend():
    return 'asyncio'
