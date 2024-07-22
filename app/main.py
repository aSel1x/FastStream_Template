import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dishka import make_async_container
from dishka.integrations import faststream as faststream_integration
from dishka.integrations import fastapi as fastapi_integration

from fastapi import FastAPI
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_faststream import AppWrapper, StreamScheduler

from app.core.config import Config
from app.core.ioc import AppProvider
from app.core.broker import new_broker
from app.core.exception.exception import (
    AppException,
    fastapi_exception_handler,
    FastStreamExceptionHandler
)

from app.routes import http, amqp

os.environ['TZ'] = 'UTC'
config = Config()

broker = new_broker(config.amqp_dsn)
broker.include_router(amqp.router)
broker.add_middleware(FastStreamExceptionHandler)

faststream_app = FastStream(broker)

taskiq_faststream_app = AppWrapper(faststream_app)

taskiq_faststream_scheduler = StreamScheduler(
    taskiq_faststream_app,
    [LabelScheduleSource(taskiq_faststream_app)]
)


@asynccontextmanager
async def faststream_lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    await broker.connect()
    yield
    await broker.close()


fastapi_app = FastAPI(
    title=config.APP_TITLE,
    root_path=config.APP_PATH,
    version=config.APP_VERSION,
    contact={
        'name': 'aSel1x',
        'url': 'https://asel1x.github.io',
        'email': 'asel1x@icloud.com',
    },
    lifespan=faststream_lifespan,
    exception_handlers={AppException: fastapi_exception_handler}
)
fastapi_app.include_router(http.router)


container = make_async_container(
    AppProvider(),
    context={
        Config: config,
        FastAPI: fastapi_app,
        RabbitBroker: broker,
        AppWrapper: taskiq_faststream_app,
        StreamScheduler: taskiq_faststream_scheduler
    }
)


def get_faststream_app() -> StreamScheduler:
    faststream_integration.setup_dishka(container, faststream_app)
    return taskiq_faststream_scheduler


def get_fastapi_app() -> FastAPI:
    fastapi_integration.setup_dishka(container, fastapi_app)
    return fastapi_app
