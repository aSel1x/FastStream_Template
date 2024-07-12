from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app import models
from app.core.security import Security
from app.services import Services

router = APIRouter()


@router.post('/', response_model=models.UserBase)
@inject
async def user_create(
        data: models.UserCreate,
        services: Depends[Services],
        security: Depends[Security]

) -> models.UserBase:
    """Create new user"""

    return await services.user.create(data, security)
