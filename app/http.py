from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.adapters.rabbitmq import AmqpQueue
from app.core.config import Config
from app.controllers import http


class FastAPIApp:
    def __init__(
            self,
            config: Config,
            adapter_amqp: AmqpQueue
    ):
        self.app = FastAPI(
            title=config.APP_TITLE,
            root_path=config.APP_PATH,
            version=config.APP_VERSION,
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

    async def initialize(self) -> FastAPI:
        http.setup_handlers(self.app)
        self.app.include_router(http.router)
        return self.app
