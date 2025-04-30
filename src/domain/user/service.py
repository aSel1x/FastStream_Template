from uuid import UUID

from domain.common.service import BaseService
from domain.user.entities import User
from domain.user.interfaces import CryptInterface, UserRepositoryInterface


class UserService(BaseService):
    def __init__(
        self, user_repo: UserRepositoryInterface, crypt: CryptInterface
    ) -> None:
        super().__init__()
        self._user_repo = user_repo
        self._crypt = crypt

    async def create(
        self,
        username: str,
        password: str,
    ) -> User:
        hashed_password = self._crypt.hash(password)
        user = User(
            username=username,
            hashed_password=hashed_password,
        )
        await self._user_repo.add(user)
        #  TODO: Record event
        return user

    async def read(
        self,
        uuid: UUID,
    ) -> User:
        user = await self._user_repo.acquire_by_uuid(uuid)
        return user

    async def check_username_exists(
        self,
        username: str,
    ) -> bool:
        if await self._user_repo.check_username_exists(username):
            raise ValueError(
                f'User with username {username} already exists'
            )  # TODO: Custom exception
