from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.fastapi import inject
from fastapi import APIRouter


from app import models
from app.adapters import AppAMQP

router = APIRouter()


@router.post('/')
@inject
async def user_create(
        data: models.UserCreate,
        amqp: Depends[AppAMQP]
) -> None:
    """Create new user"""

    await amqp.create_task(
        data,
        queue='create_user',
        exchange='users',
    )
