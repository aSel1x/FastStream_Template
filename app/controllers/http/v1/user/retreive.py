from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app import models
from app.controllers.http import deps
from app.usecases import Services

router = APIRouter()


@router.post('/auth', response_model=models.UserAuth)
@inject
async def user_auth(
        data: models.UserCreate,
        services: Depends[Services],
) -> models.UserAuth:
    return await services.user.auth(
        username=data.username,
        password=data.password,
    )


@router.get('/', response_model=models.UserBase)
@inject
async def user_retrieve(
        user: deps.CurrentUser
) -> models.UserBase:
    """Get current user"""

    return models.UserBase(**user.model_dump())
