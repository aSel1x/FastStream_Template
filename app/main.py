import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations import fastapi as fastapi_integration
from dishka.integrations import faststream as faststream_integration
from fastapi import FastAPI
from faststream.rabbit import RabbitBroker

from app.controllers import http, amqp
from app.core.amqp import AppAMQP
from app.core.config import Config
from app.core.ioc import AppProvider

os.environ['TZ'] = 'UTC'

config = Config()
broker = RabbitBroker(config.amqp_dsn.unicode_string())
broker.include_router(amqp.router)

amqp_app = AppAMQP(broker)


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
)
fastapi_app.include_router(http.router)
http.setup_handlers(fastapi_app)

container = make_async_container(
    AppProvider(),
    context={
        Config: config,
        FastAPI: fastapi_app,
        AppAMQP: amqp_app
    }
)


def get_amqp_worker() -> amqp_app.taskiq_scheduler:
    faststream_integration.setup_dishka(container, amqp_app.faststream_app)
    return amqp_app.taskiq_scheduler


def get_http_worker() -> FastAPI:
    fastapi_integration.setup_dishka(container, fastapi_app)
    return fastapi_app
