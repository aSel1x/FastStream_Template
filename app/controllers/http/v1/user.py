from typing import Annotated

from dishka.integrations.base import FromDishka as Depends
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, status, Body
from fastapi.responses import Response

from app import models
from app.controllers.http import deps
from app.usecases import Services

router = APIRouter(prefix="/user", tags=["user"])


@router.post('/', response_class=Response, status_code=status.HTTP_201_CREATED)
@inject
async def user_create(
        data: models.UserCreate,
        service: Depends[Services]
) -> None:
    """Create new user"""
    await service.adapters.rabbit.create_task(data, 'create', exchange='user')


@router.post('/oauth2', response_model=models.UserAuth)
@inject
async def user_oauth2(
        data: models.UserCreate,
        services: Depends[Services],
) -> models.UserAuth:
    """Authenticate user and return oauth2 credentials"""
    user = await services.user.authenticate(data)
    return await services.user.oauth2(user)


@router.get('/', response_model=models.UserBase)
@inject
async def user_retrieve(
        user: deps.CurrentUser,
) -> models.UserBase:
    """Get current user"""
    return models.UserBase.model_validate(user)


@router.post('/oauth2/refresh', response_model=models.UserAuth)
@inject
async def user_oauth2_refresh(
        refresh_token: Annotated[str, Body(embed=True)],
        services: Depends[Services],
) -> models.UserAuth:
    """Refresh oauth2 credentials"""
    return await services.user.refresh_oauth2(refresh_token)
