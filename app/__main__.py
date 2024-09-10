import asyncio
import os

import uvicorn
from dishka import AsyncContainer, make_async_container
from dishka.integrations import fastapi as fastapi_integration
from dishka.integrations import faststream as faststream_integration
from loguru import logger

from app.adapters.adapters import Adapters
from app.core.config import Config
from app.core.ioc import AppProvider

from .amqp import FastStreamApp
from .http import FastAPIApp

os.environ['TZ'] = 'UTC'
config = Config()


async def get_adapters() -> Adapters:
    async with Adapters.create(config) as adapters:
        return adapters


async def make_container() -> AsyncContainer:
    adapters = await get_adapters()
    return make_async_container(
        AppProvider(),
        context={
            Config: config,
            Adapters: adapters
        }
    )


async def setup_http() -> FastAPIApp:
    adapters = await get_adapters()
    container = await make_container()
    http_app = await FastAPIApp(config, adapters.rabbit).initialize()
    fastapi_integration.setup_dishka(container, http_app.app)
    return http_app


async def setup_amqp() -> FastStreamApp:
    adapters = await get_adapters()
    container = await make_container()
    amqp_app = await FastStreamApp(config, adapters.rabbit).initialize()
    faststream_integration.setup_dishka(container, adapters.rabbit.faststream_app)
    return amqp_app


async def run_app() -> None:
    amqp_app = await setup_amqp()
    http_app = await setup_http()
    await asyncio.gather(
        amqp_app.app.taskiq_scheduler.startup(),
        uvicorn.Server(
            uvicorn.Config(http_app.app, host='0.0.0.0')
        ).serve()
    )


if __name__ == '__main__':
    try:
        asyncio.run(run_app())
    except KeyboardInterrupt:
        logger.info('App close')
