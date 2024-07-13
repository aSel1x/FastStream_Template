from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.fastapi import inject
from fastapi import APIRouter
from faststream.rabbit import RabbitBroker

from app import models

router = APIRouter()


@router.post('/')
@inject
async def user_create(
        data: models.UserCreate,
        broker: Depends[RabbitBroker]
) -> None:
    """Create new user"""

    await broker.publish(data, 'create_user')
