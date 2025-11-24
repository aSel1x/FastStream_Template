from typing import override

from domain.user import entities
from domain.user.interfaces import UserRepositoryInterface
from domain.user.value_objects import Email, UserID, Username
from infrastructure.utils import singleton


@singleton
class InMemoryUserRepo(UserRepositoryInterface):
    def __init__(self) -> None:
        self._users: dict[UserID, entities.User] = {}

    @override
    async def acquire_by_id(self, user_id: UserID) -> entities.User | None:
        return self._users.get(user_id)

    @override
    async def acquire_by_username(self, username: Username) -> entities.User | None:
        for user in self._users.values():
            if user.username.to_raw() == username.to_raw():
                return user
        return None

    @override
    async def acquire_by_email(self, email: Email) -> entities.User | None:
        if email.to_raw() is None:
            return None
        for user in self._users.values():
            if user.email.to_raw() == email.to_raw():
                return user
        return None

    @override
    async def add(self, user: entities.User) -> None:
        self._users[user.id] = user

    @override
    async def update(self, user: entities.User) -> None:
        self._users[user.id] = user

    @override
    async def check_username_exists(self, username: Username) -> bool:
        for user in self._users.values():
            if user.username.to_raw() == username.to_raw():
                return True
        return False

    @override
    async def check_email_exists(self, email: Email) -> bool:
        if email.to_raw() is None:
            return False
        for user in self._users.values():
            if user.email.to_raw() == email.to_raw():
                return True
        return False
