from uuid import UUID

from application.user import dto
from domain.user import entities
from domain.user.interfaces import UserRepositoryInterface


class InMemoryUserRepo(UserRepositoryInterface):
    def __init__(self):
        self._users: dict[UUID, entities.User] = {}

    async def acquire_by_uuid(self, user_uuid: UUID) -> dto.UserDTO:
        if user_uuid not in self._users:
            raise  #  TODO: UserNotFoundException
        return self._users[user_uuid]

    async def add(self, user: entities.User) -> None:
        self._users[user.uuid] = user

    async def check_username_exists(self, username: str) -> bool:
        for user in self._users.values():
            if user.username == username:
                return True
