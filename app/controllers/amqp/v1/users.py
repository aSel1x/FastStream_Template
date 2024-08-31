from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.faststream import inject
from faststream.rabbit import RabbitRouter
from faststream.rabbit.annotations import Logger

from app import models
from app.usecases import Services

router = RabbitRouter()


@router.subscriber('create_user', 'users')
@router.publisher('user_status', 'users')
@inject
async def users(
        data: models.UserCreate,
        logger: Logger,
        services: Depends[Services],
):
    user = await services.user.create(
        user=data,
    )
    logger.info(f"User {data.username} created")
    return user
