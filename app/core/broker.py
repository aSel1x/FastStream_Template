from faststream.rabbit import RabbitBroker
from pydantic import AmqpDsn


def new_broker(amqp_dsn: AmqpDsn) -> RabbitBroker:
    return RabbitBroker(url=amqp_dsn.unicode_string())
