from dishka.entities.depends_marker import FromDishka as Depends
from dishka.integrations.faststream import inject
from faststream.rabbit import RabbitRouter
from loguru import logger

from app import models
from app.usecases import Services

router = RabbitRouter()


@router.subscriber('create', 'user')
@router.publisher('response', 'user')
@inject
async def user_create(
    data: models.UserCreate,
    service: Depends[Services],
):
    user = await service.user.create(data)
    logger.info(f"User {data.username} created")
    return user
