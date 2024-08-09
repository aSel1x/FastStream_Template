import datetime as dt
from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from taskiq_faststream.types import ScheduledTask


from app import models
from app.core.amqp import AppAMQP

router = APIRouter()


@router.post('/')
@inject
async def user_create(
        data: models.UserCreate,
        amqp: Depends[AppAMQP]
) -> None:
    """Create new user"""

    await amqp.broker.publish(
        data,
        queue='create_user',
        exchange='users',
    )
