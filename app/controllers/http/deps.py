from typing import Annotated

from dishka.entities.depends_marker import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Depends as FromFastAPI
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import models
from app.usecases import Services


@inject
async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, FromFastAPI(HTTPBearer())],
    service: FromDishka[Services],
) -> models.User | None:
    return await service.user.retrieve_by_token(creds.credentials)


CurrentUser = Annotated[models.User, FromFastAPI(get_current_user)]
