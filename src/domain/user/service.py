from domain.common.entity import EntityUUID
from domain.common.service import BaseService
from domain.user.entities import User
from domain.user.events import (
    UserAuthenticatedEvent,
    UserCreatedEvent,
    UserDeletedEvent,
    UserProfileUpdatedEvent,
)
from domain.user.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    UserIdNotExistError,
    UserIsDeletedError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from domain.user.interfaces import CryptInterface, UserRepositoryInterface
from domain.user.value_objects import (
    DeletionTime,
    Email,
    HashedPassword,
    PlainPassword,
    Username,
)


class UserService(BaseService):
    def __init__(
        self, user_repo: UserRepositoryInterface, crypt: CryptInterface
    ) -> None:
        super().__init__()
        self._user_repo: UserRepositoryInterface = user_repo
        self._crypt: CryptInterface = crypt

    async def create(
        self,
        username: Username,
        email: Email | None = None,
        password: PlainPassword | None = None,
    ) -> User:
        username_exists = await self._user_repo.check_username_exists(username)
        if username_exists:
            raise UsernameAlreadyExistsError(username.to_raw())

        if email and email.to_raw():
            email_exists = await self._user_repo.check_email_exists(email)
            if email_exists:
                raise EmailAlreadyExistsError(email.to_raw())

        if password is None:
            raise ValueError('Password is required')

        hashed_password = await self._crypt.hash(password.to_raw())
        hashed_password_vo = HashedPassword(hashed_password)

        user = User(
            username=username,
            email=email or Email(None),
            hashed_password=hashed_password_vo,
        )
        await self._user_repo.add(user)
        self._record_event(
            UserCreatedEvent(
                user_id=user.uuid.to_raw(),
                username=user.username.to_raw(),
                email=user.email.to_raw() if user.email.to_raw() else None,
            )
        )

        return user

    async def authenticate(
        self,
        password: PlainPassword,
        username: str | None = None,
        email: str | None = None,
    ) -> User:
        if not username and not email:
            raise InvalidCredentialsError()

        user: User | None = None

        if username:
            user = await self._user_repo.acquire_by_username(Username(username))
        elif email:
            user = await self._user_repo.acquire_by_email(Email(email))

        if user is None:
            raise InvalidCredentialsError()

        self._validate_user_not_deleted(user)

        password_matches = await self._crypt.compare_hashes(
            password.to_raw(), user.hashed_password.to_raw()
        )
        if not password_matches:
            raise InvalidCredentialsError()

        self._record_event(
            UserAuthenticatedEvent(
                user_id=user.uuid.to_raw(),
                username=user.username.to_raw(),
            )
        )

        return user

    async def delete_user(self, user_id: EntityUUID) -> None:
        user = await self._user_repo.acquire_by_uuid(user_id)
        if user is None:
            raise UserIdNotExistError(user_id.to_raw())
        self._validate_user_not_deleted(user)

        user.deleted_at = DeletionTime.create_deleted()
        await self._user_repo.update(user)
        self._record_event(UserDeletedEvent(user_id=user_id.to_raw()))

    async def get_user_by_uuid(self, user_id: EntityUUID) -> User:
        user = await self._user_repo.acquire_by_uuid(user_id)
        if user is None:
            raise UserNotFoundError()
        self._validate_user_not_deleted(user)
        return user

    async def update_user(
        self,
        user: User,
        username: Username | None = None,
        email: Email | None = None,
    ) -> User:
        self._validate_user_not_deleted(user)

        updated_fields: list[str] = []

        if username is not None and username.to_raw() != user.username.to_raw():
            username_exists = await self._user_repo.check_username_exists(username)
            if username_exists:
                raise UsernameAlreadyExistsError(username.to_raw())
            user.update_username(username)
            updated_fields.append('username')

        if email is not None and email.to_raw() != user.email.to_raw():
            email_exists = await self._user_repo.check_email_exists(email)
            if email_exists:
                raise EmailAlreadyExistsError(email.to_raw())
            user.update_email(email)
            updated_fields.append('email')

        await self._user_repo.update(user)
        if updated_fields:
            self._record_event(
                UserProfileUpdatedEvent(
                    user_id=user.uuid.to_raw(),
                    updated_fields=tuple(updated_fields),
                )
            )

        return user

    def _validate_user_not_deleted(self, user: User) -> None:
        if user.deleted_at.is_deleted():
            raise UserIsDeletedError(user.uuid.to_raw())
