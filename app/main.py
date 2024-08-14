import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations import fastapi as fastapi_integration
from dishka.integrations import faststream as faststream_integration
from fastapi import FastAPI
from faststream.rabbit import RabbitBroker
from taskiq_faststream import StreamScheduler

from app.controllers import amqp, http
from app.adapters import AppAMQP
from app.core.config import Config
from app.core.ioc import AppProvider

os.environ['TZ'] = 'UTC'


class App:
    def __init__(self):
        self.config = Config()

        self.broker = self.get_broker()
        self.amqp_app = AppAMQP(self.broker)

        self.container = make_async_container(
            AppProvider(),
            context={
                Config: self.config,
                AppAMQP: self.amqp_app
            }
        )

    def get_broker(self) -> RabbitBroker:
        broker = RabbitBroker(self.config.amqp_dsn.unicode_string())
        broker.include_router(amqp.router)
        return broker

    def get_fastapi_app(self) -> FastAPI:
        @asynccontextmanager
        async def faststream_lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
            await self.broker.connect()
            yield
            await self.broker.close()

        fastapi_app = FastAPI(
            title=self.config.APP_TITLE,
            root_path=self.config.APP_PATH,
            version=self.config.APP_VERSION,
            contact={
                'name': 'aSel1x',
                'url': 'https://asel1x.github.io',
                'email': 'asel1x@icloud.com',
            },
            lifespan=faststream_lifespan,
        )
        fastapi_app.include_router(http.router)
        http.setup_handlers(fastapi_app)
        return fastapi_app

    def get_amqp_worker(self) -> StreamScheduler:
        faststream_integration.setup_dishka(self.container, self.amqp_app.faststream_app)
        return self.amqp_app.taskiq_scheduler

    def get_http_worker(self) -> FastAPI:
        http_app = self.get_fastapi_app()
        fastapi_integration.setup_dishka(self.container, http_app)
        return http_app
