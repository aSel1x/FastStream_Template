from dishka.entities.depends_marker import FromDishka as Depends
from dishka.integrations.faststream import inject
from faststream.rabbit.annotations import RabbitMessage
from faststream.rabbit.router import RabbitRouter
from faststream.rabbit.schemas.constants import ExchangeType
from faststream.rabbit.schemas.exchange import RabbitExchange
from faststream.rabbit.schemas.queue import RabbitQueue
from loguru import logger

from app.core import exception
from app.usecases import Services

router = RabbitRouter()


@router.subscriber(
    RabbitQueue(
        'taskiq',
        arguments={
            'x-dead-letter-exchange': '',
            'x-dead-letter-routing-key': 'taskiq.dead_letter',
        },
    ),
    RabbitExchange('taskiq', ExchangeType.TOPIC),
)
@inject
async def taskiq_distribution(
    msg: RabbitMessage,
    service: Depends[Services],
) -> None:
    decoded_body = await msg.decode()
    if not isinstance(decoded_body, dict):
        raise exception.system.BrokerMessage

    task = decoded_body.get('kwargs')
    if not isinstance(task, dict):
        raise exception.system.BrokerMessage

    entity = task.get('entity', {})
    queue = task.get('queue')
    exchange = task.get('exchange')

    if not isinstance(queue, str):
        return await msg.nack(requeue=False)

    if not isinstance(exchange, str):
        exchange = None

    await service.adapters.rabbit.create_task(
        entry=entity, queue=queue, exchange=exchange
    )
    logger.info(f"{decoded_body.get("task_name")} published to {exchange}:{queue}")
