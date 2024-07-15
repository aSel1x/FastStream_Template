from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.faststream import inject
from faststream.rabbit import RabbitRouter
from faststream.rabbit.annotations import Logger

from app import models
from app.core.security import Security
from app.services import Services

router = RabbitRouter()


@router.subscriber('create_user')
@router.publisher('user_status')
@inject
async def users(
        data: models.UserCreate,
        logger: Logger,
        services: Depends[Services],
        security: Depends[Security]
):
    user = await services.user.create(
        user=data,
        security=security
    )
    logger.info(f"User {data.username} created")
    return user
