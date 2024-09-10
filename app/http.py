from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.adapters.rabbitmq import AmqpQueue
from app.controllers import http
from app.core.config import Config


class FastAPIApp:
    def __init__(
            self,
            config: Config,
            adapter_amqp: AmqpQueue
    ):
        self.app = FastAPI(
            title=config.app.name,
            root_path=config.app.path,
            version=config.app.version,
            contact={
                'name': 'aSel1x',
                'url': 'https://asel1x.github.io',
                'email': 'asel1x@icloud.com',
            },
            lifespan=self.__rabbit_connection
        )
        self.adapter_amqp = adapter_amqp

    @asynccontextmanager
    async def __rabbit_connection(self, _: FastAPI):
        await self.adapter_amqp.broker.connect()
        yield
        await self.adapter_amqp.broker.close()

    async def initialize(self) -> 'FastAPIApp':
        http.setup_handlers(self.app)
        self.app.include_router(http.router)
        return self
