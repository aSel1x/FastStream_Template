import logging

from dishka import make_async_container
from dishka.integrations.faststream import setup_dishka
from faststream import FastStream
from faststream.rabbit import RabbitBroker

from infrastructure.cache.config import CacheConfig
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.di import AppProvider
from infrastructure.email import EmailConfig
from infrastructure.hydra import HydraConfig
from infrastructure.observability.logging import configure_logging
from infrastructure.queue.config import RabbitMQConfig
from infrastructure.security.rate_limiter import RateLimitConfig
from infrastructure.settings import Settings
from presentation.amqp.consumers.user import router as user_events_router

logger = logging.getLogger(__name__)


def create_app() -> FastStream:
    """The AMQP entrypoint, wired from the same container as the HTTP app.

    It used to build its broker by hand with no DI at all, so a consumer could not reach a
    repository or a use case without constructing one itself — and any dependency added to
    the graph had to be wired a second time here.
    """
    settings = Settings.load()
    configure_logging()

    container = make_async_container(
        AppProvider(),
        context={
            HydraConfig: settings.hydra,
            RabbitMQConfig: settings.rabbitmq,
            SQLAlchemyConfig: settings.database,
            EmailConfig: settings.email,
            RateLimitConfig: settings.rate_limit,
            CacheConfig: settings.cache,
        },
    )

    broker = RabbitBroker(settings.rabbitmq.url)
    broker.include_router(user_events_router)

    app = FastStream(broker)
    setup_dishka(container, app, auto_inject=True)

    logger.info('FastStream application created')
    return app


app = create_app()
