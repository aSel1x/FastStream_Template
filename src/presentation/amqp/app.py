import logging

from faststream import FastStream
from faststream.rabbit import RabbitBroker
from infrastructure.queue.config import RabbitMQConfig

from presentation.amqp.consumers.user import router as user_events_router

logger = logging.getLogger(__name__)


def create_app() -> FastStream:
    config = RabbitMQConfig.from_environ()

    broker = RabbitBroker(config.url)

    broker.include_router(user_events_router)

    app = FastStream(broker)

    logger.info('FastStream application created with RabbitMQ broker')
    return app


app = create_app()
