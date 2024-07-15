from contextlib import asynccontextmanager
from typing import ParamSpec, AsyncGenerator

from dishka import make_async_container
from dishka.integrations import faststream as faststream_integration
from dishka.integrations import fastapi as fastapi_integration

from faststream import FastStream
from fastapi import FastAPI

from app.core.config import Config
from app.core.ioc import AppProvider
from app.core.broker import new_broker
from app.core.exception.http import HTTPException, fastapi_exception_handler

from app.routes import http, amqp

config = Config()
container = make_async_container(AppProvider(), context={Config: config})


def get_faststream_app() -> FastStream:
    broker = new_broker(config.amqp_dsn)
    faststream_app = FastStream(broker)
    faststream_integration.setup_dishka(container, faststream_app, auto_inject=True)
    broker.include_router(amqp.router)
    return faststream_app


def get_fastapi_app(lifespan: ParamSpec | None = None) -> FastAPI:
    fastapi_app = FastAPI(
        title=config.APP_TITLE,
        root_path=config.APP_PATH,
        version=config.APP_VERSION,
        contact={
            'name': 'aSel1x',
            'url': 'https://asel1x.github.io',
            'email': 'asel1x@icloud.com',
        },
        lifespan=lifespan,
        exception_handlers={HTTPException: fastapi_exception_handler}
    )
    fastapi_integration.setup_dishka(container, fastapi_app)
    fastapi_app.include_router(http.router)

    return fastapi_app


def get_app():
    faststream_app = get_faststream_app()

    @asynccontextmanager
    async def faststream_lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        await faststream_app.broker.start()
        yield
        await faststream_app.broker.close()

    fastapi_app = get_fastapi_app(faststream_lifespan)

    return fastapi_app
