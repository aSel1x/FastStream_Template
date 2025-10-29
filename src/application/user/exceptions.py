from dataclasses import dataclass
from typing import override
from uuid import UUID

from application.common.exceptions import BaseApplicationError


@dataclass(eq=False)
class UserIdAlreadyExistsError(BaseApplicationError):
    user_id: UUID

    @property
    @override
    def detail(self) -> str:
        return f'A user with the "{self.user_id}" user_id already exists'


@dataclass(eq=False)
class UserIdNotExistError(BaseApplicationError):
    user_id: UUID

    @property
    @override
    def detail(self) -> str:
        return f'A user with "{self.user_id}" user_id doesn\'t exist'


@dataclass(eq=False)
class UsernameNotExistError(BaseApplicationError):
    username: str

    @property
    @override
    def detail(self) -> str:
        return f'A user with "{self.username}" username doesn\'t exist'
