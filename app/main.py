import os

from dishka import AsyncContainer, make_async_container
from dishka.integrations import fastapi as fastapi_integration
from dishka.integrations import faststream as faststream_integration
from dishka.integrations import taskiq as taskiq_integration

from app.adapters.rabbitmq import RabbitQueue
from app.core.config import Config
from app.core.ioc import AppProvider

from .fastapi import FastAPIApp
from .faststream import FastStreamApp
from .taskiq import TaskIqApp

os.environ['TZ'] = 'UTC'
config = Config()


def make_container() -> AsyncContainer:
    return make_async_container(
        AppProvider(),
        context={
            Config: config,
        }
    )


def setup_fastapi() -> FastAPIApp:
    container = make_container()
    fastapi_app = FastAPIApp(config).initialize()
    fastapi_integration.setup_dishka(container, fastapi_app.app)
    return fastapi_app


def setup_faststream() -> FastStreamApp:
    container = make_container()
    faststream_app = FastStreamApp(config).initialize()
    RabbitQueue(
        rabbit_dsn=config.rabbit.dsn,
        redis_dsn=config.redis.dsn,
        faststream_broker=faststream_app.broker,
        faststream_app=faststream_app.app,
    )
    faststream_integration.setup_dishka(container, faststream_app.app)
    return faststream_app


def setup_taskiq() -> TaskIqApp:
    container = make_container()
    taskiq_app = TaskIqApp(config).initialize()
    RabbitQueue(
        rabbit_dsn=config.rabbit.dsn,
        redis_dsn=config.redis.dsn,
        taskiq_broker=taskiq_app.broker,
        taskiq_scheduler=taskiq_app.scheduler,
    )
    taskiq_integration.setup_dishka(container, taskiq_app.broker)
    return taskiq_app
