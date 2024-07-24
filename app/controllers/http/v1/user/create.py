import datetime as dt
from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from faststream.rabbit import RabbitBroker
from taskiq_faststream import AppWrapper
from taskiq_faststream.types import ScheduledTask

from app import models

router = APIRouter()


@router.post('/')
@inject
async def user_create(
        data: models.UserCreate,
        taskiq: Depends[AppWrapper],
) -> None:
    """Create new user"""

    taskiq.task(
        data,
        queue='create_user',
        exchange='users',
        schedule=[
            ScheduledTask(time=(dt.datetime.now() + dt.timedelta(seconds=30)))
        ]
    )
