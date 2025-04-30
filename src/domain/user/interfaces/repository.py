from domain.user.entities import User


class UserRepositoryInterface:
    """
    User repository interface.
    """

    async def acquire_by_uuid(self, user_id: str) -> User | None:
        """
        Acquire a user by ID.
        """
        raise NotImplementedError

    async def add(self, user: User) -> None:
        """
        Add a new user.
        """
        raise NotImplementedError

    async def check_username_exists(self, username: str) -> bool:
        """
        Check if a username already exists.
        """
        raise NotImplementedError
