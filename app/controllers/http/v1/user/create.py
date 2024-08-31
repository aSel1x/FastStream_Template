from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.fastapi import inject
from fastapi import APIRouter


from app import models
from app.usecases import Services

router = APIRouter()


@router.post('/')
@inject
async def user_create(
        data: models.UserCreate,
        service: Depends[Services]
) -> None:
    """Create new user"""

    await service.adapters.amqp.create_task(
        data,
        queue='create_user',
        exchange='users',
    )
