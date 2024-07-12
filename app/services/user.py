from sqlmodel.ext.asyncio.session import AsyncSession

from app import models
from app.core import exps
from app.core.security import Security
from app.repositories.user import UserRepository


class UserService:

    def __init__(self, session: AsyncSession):
        self.db = UserRepository(session)

    async def create(self, user: models.UserCreate, security: Security) -> models.UserBase:
        if await self.db.retrieve_by_username(user.username):
            raise exps.USER_EXISTS

        user.password = security.pwd.hashpwd(user.password)
        user = await self.db.create(models.User(**user.model_dump()))
        return models.UserBase(**user.model_dump())

    async def auth(self, username: str, password: str, security: Security) -> models.UserAuth:
        if not (user := await self.db.retrieve_by_username(username)):
            raise exps.USER_NOT_FOUND
        if not security.pwd.checkpwd(password, user.password):
            raise exps.USER_IS_CORRECT

        return models.UserAuth(
            token=security.jwt.encode_token({'id': user.id}, 1440)
        )

    async def retrieve_by_token(self, token: str, security: Security) -> models.User | None:
        if not (payload := security.jwt.decode_token(token)):
            return None
        if not (
            user := await self.db.retrieve_one(
                ident=payload.get('id')
            )
        ):
            raise exps.USER_NOT_FOUND
        else:
            return user
