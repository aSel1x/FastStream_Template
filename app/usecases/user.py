from typing import TYPE_CHECKING

from app import models
from app.core import exception

if TYPE_CHECKING:
    from app.usecases import Services


class UserService:

    def __init__(self, service: 'Services'):
        self.service = service

    async def create(self, user: models.UserCreate) -> models.User:
        if await self.service.adapters.postgres.user.retrieve_by_username(user.username):
            raise exception.user.UsernameTaken

        user.password = self.service.security.pwd.hashpwd(user.password)
        user = await self.service.adapters.postgres.user.create(models.User.model_validate(user))
        await self.service.adapters.redis.user.create(user)
        return user

    async def auth(self, username: str, password: str) -> models.UserAuth:
        if not (user := await self.service.adapters.postgres.user.retrieve_by_username(username)):
            raise exception.user.NotFound
        if not self.service.security.pwd.checkpwd(password, user.password):
            raise exception.user.PasswordWrong

        return models.UserAuth(
            token=self.service.security.jwt.encode_token({'id': user.id}, 1440)
        )

    async def retrieve_by_token(self, token: str) -> models.User | None:
        if (payload := self.service.security.jwt.decode_token(token)) is None:
            return None
        if (ident := payload.get('id')) is None:
            return None
        if (user := await self.service.adapters.redis.user.retrieve_one(ident=ident)) is not None:
            return user
        if (user := await self.service.adapters.postgres.user.retrieve_one(ident=ident)) is not None:
            return user
        raise exception.user.NotFound
