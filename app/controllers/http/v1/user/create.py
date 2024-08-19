from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.fastapi import inject
from fastapi import APIRouter


from app import models
from app.adapters import AMQP

router = APIRouter()


@router.post('/')
@inject
async def user_create(
        data: models.UserCreate,
        amqp: Depends[AMQP]
) -> None:
    """Create new user"""

    await amqp.create_task(
        data,
        queue='create_user',
        exchange='users',
    )
