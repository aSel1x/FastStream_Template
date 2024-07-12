from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.faststream import inject
from faststream.rabbit import RabbitRouter

from app import models
from app.core.security import Security
from app.services import Services

router = RabbitRouter()


@router.subscriber('crete_user')
@router.publisher('user_status')
@inject
async def users(
        data: models.UserCreate,
        services: Depends[Services],
        security: Depends[Security]
):
    user = await services.user.create(
        user=data,
        security=security
    )
    return user
