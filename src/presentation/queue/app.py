import logging

from faststream import FastStream
from infrastructure.queue.broker import create_broker
from infrastructure.queue.config import RabbitMQConfig

from presentation.queue.consumers.user_events import router as user_events_router

logger = logging.getLogger(__name__)


def create_app() -> FastStream:
    config = RabbitMQConfig.from_environ()

    broker = create_broker(config)

    broker.include_router(user_events_router)

    app = FastStream(broker)

    logger.info('FastStream application created with RabbitMQ broker')
    return app


app = create_app()
