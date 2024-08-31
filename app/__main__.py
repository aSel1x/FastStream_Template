import asyncio
import os

import uvicorn
from dishka import make_async_container
from dishka.integrations import fastapi as fastapi_integration
from dishka.integrations import faststream as faststream_integration
from loguru import logger

from app.adapters.adapters import Adapters
from app.adapters.rabbitmq import AmqpQueue
from app.core.config import Config
from app.core.ioc import AppProvider

from .amqp import FastStreamApp
from .http import FastAPIApp

os.environ['TZ'] = 'UTC'


async def setup_app():
    config = Config()

    async with Adapters.get_rabbitmq(config.amqp_dsn) as adapter_amqp:
        container = make_async_container(
            AppProvider(),
            context={
                Config: config,
                AmqpQueue: adapter_amqp
            }
        )

        http_app = await FastAPIApp(config, adapter_amqp).initialize()
        fastapi_integration.setup_dishka(container, http_app)

        amqp_worker = await FastStreamApp(config, adapter_amqp).initialize()
        faststream_integration.setup_dishka(container, adapter_amqp.faststream_app)

        config = uvicorn.Config(app=http_app, host='0.0.0.0', port=8000)
        server = uvicorn.Server(config)

        return amqp_worker, server


async def run_app():
    amqp_worker, server = await setup_app()
    await asyncio.gather(
        amqp_worker.startup(),
        server.serve()
    )


if __name__ == '__main__':
    try:
        asyncio.run(run_app())
    except KeyboardInterrupt:
        logger.info('App close')
