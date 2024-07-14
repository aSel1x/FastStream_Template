from typing import Annotated

from dishka.integrations.base import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Depends as FromFastAPI
from fastapi.security import APIKeyHeader

from app import models
from app.core import exps
from app.core.security import Security
from app.services import Services


@inject
async def get_current_user(
    token: Annotated[str, FromFastAPI(APIKeyHeader(name='access-token'))],
    services: FromDishka[Services],
    security: FromDishka[Security],
) -> models.User | None:
    if user := await services.user.retrieve_by_token(token, security):
        return user
    raise exps.USER_NOT_FOUND

CurrentUser = Annotated[models.User, FromFastAPI(get_current_user)]
