from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.faststream import inject
from faststream.rabbit.annotations import RabbitMessage
from faststream.rabbit.router import RabbitRouter
from faststream.rabbit.schemas.exchange import ExchangeType, RabbitExchange
from faststream.rabbit.schemas.queue import RabbitQueue
from loguru import logger

from app.usecases import Services

router = RabbitRouter()


@router.subscriber(
    RabbitQueue(
        'taskiq',
        arguments={
            'x-dead-letter-exchange': '',
            'x-dead-letter-routing-key': 'taskiq.dead_letter',
        }
    ),
    RabbitExchange(
        'taskiq',
        ExchangeType.TOPIC
    )
)
@inject
async def taskiq_distribution(
        msg: RabbitMessage,
        service: Depends[Services],
) -> None:
    task: dict = msg.decoded_body.get('kwargs')
    entity = task.get('entity', {})
    queue = task.get('queue')
    exchange = task.get('exchange')

    if queue is None:
        return await msg.nack(requeue=False)

    await service.adapters.rabbit.create_task(
        entry=entity,
        queue=queue,
        exchange=exchange
    )
    logger.info(f"{msg.decoded_body.get("task_name")} published to {exchange}:{queue}")
