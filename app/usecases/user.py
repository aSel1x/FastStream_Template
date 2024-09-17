import time
from typing import TYPE_CHECKING

from app import models
from app.core import exception

if TYPE_CHECKING:
    from app.usecases import Services


class UserService:

    def __init__(self, service: 'Services'):
        self.service = service

    async def create(self, user: models.UserCreate) -> models.User:
        if (
            await self.service.adapters.redis.user.username_check(user.username)
            is not None
        ):
            raise exception.user.UsernameTaken
        await self.service.adapters.redis.user.username_take(user.username)
        _user: models.User = models.User.model_validate(
            user, update=dict(password=self.service.security.pwd.hashpwd(user.password))
        )
        _user = await self.service.adapters.postgres.user.create(_user)
        await self.service.adapters.redis.user.create(_user)
        return _user

    async def authenticate(self, user: models.UserCreate) -> models.User:
        if not (
            _user := await self.service.adapters.postgres.user.retrieve_by_username(
                user.username
            )
        ):
            raise exception.user.NotFound
        if not self.service.security.pwd.checkpwd(user.password, _user.password):
            raise exception.user.PasswordWrong
        return _user

    async def oauth2(self, user: models.User) -> models.UserAuth:
        expires_in = 3600
        access_token = self.service.security.jwt.encode(
            {'id': user.id}, time.time() + expires_in
        )
        refresh_token = self.service.security.jwt.encode({'id': user.id})
        return models.UserAuth(
            access_token=access_token,
            token_type='Bearer',
            expires_in=expires_in,
            refresh_token=refresh_token,
        )

    async def retrieve_by_token(self, token: str) -> models.User:
        if (payload := self.service.security.jwt.decode(token)) is None:
            raise exception.token.TokenPayload
        if (ident := payload.get('id')) is None:
            raise exception.token.TokenPayloadUser
        if (
            user := await self.service.adapters.redis.user.retrieve_one(ident=ident)
        ) is not None:
            return user
        if (
            user := await self.service.adapters.postgres.user.retrieve_one(ident=ident)
        ) is not None:
            await self.service.adapters.redis.user.create(user)
            return user
        raise exception.user.NotFound

    async def refresh_oauth2(self, refresh_token: str) -> models.UserAuth:
        user = await self.retrieve_by_token(refresh_token)
        return await self.oauth2(user)
