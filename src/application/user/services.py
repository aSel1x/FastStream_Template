import secrets
from datetime import UTC, datetime, timedelta
from typing import final
from uuid import UUID, uuid4

from application.common.interfaces import UnitOfWorkInterface
from domain.user.entities import User
from domain.user.entities.session import DeviceInfo, RefreshToken, SessionAggregate
from domain.user.exceptions import (
    AccountLockedError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    RefreshTokenReuseError,
    UserIsDeletedError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from domain.user.interfaces import (
    CryptInterface,
    SessionRepositoryInterface,
    UserRepositoryInterface,
)
from domain.user.value_objects import (
    Email,
    HashedPassword,
    PlainPassword,
    TokenHash,
    UserID,
    Username,
)


@final
class UserService:
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15
    SESSION_EXPIRE_SECONDS = 60 * 60 * 24 * 30
    REFRESH_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 7

    def __init__(
        self,
        user_repo: UserRepositoryInterface,
        session_repo: SessionRepositoryInterface,
        crypt: CryptInterface,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_repo: UserRepositoryInterface = user_repo
        self._session_repo: SessionRepositoryInterface = session_repo
        self._crypt: CryptInterface = crypt
        # Every aggregate this service mutates is registered here, so its events reach the
        # outbox even when the calling use case never sees the aggregate. Session revocation
        # triggered by a password change is exactly that case.
        self._uow: UnitOfWorkInterface = uow

    async def create(
        self,
        user_id: UserID,
        username: Username,
        password: PlainPassword,
        email: Email | None = None,
        verification_token: str | None = None,
    ) -> User:
        username_exists = await self._user_repo.check_username_exists(username)
        if username_exists:
            raise UsernameAlreadyExistsError(username.to_raw())

        effective_email = email or Email(None)
        if effective_email.to_raw():
            email_exists = await self._user_repo.check_email_exists(effective_email)
            if email_exists:
                raise EmailAlreadyExistsError(effective_email.to_raw())

        hashed_password_bytes = await self._crypt.hash(password.to_raw())
        hashed_password_vo = HashedPassword(hashed_password_bytes)

        token = verification_token or str(uuid4())

        user = User.create(
            user_id=user_id,
            username=username,
            email=effective_email,
            hashed_password=hashed_password_vo,
            verification_token=token,
        )

        await self._user_repo.add(user)
        self._uow.register(user)
        return user

    async def authenticate(
        self,
        password: PlainPassword,
        username: str | None = None,
        email: str | None = None,
        device_info: DeviceInfo | None = None,
    ) -> tuple[User | None, SessionAggregate | None, str | None]:
        if not username and not email:
            return None, None, None

        user: User | None = None

        if username:
            user = await self._user_repo.acquire_by_username(Username(username))
        elif email:
            user = await self._user_repo.acquire_by_email(Email(email))

        if user is None:
            return None, None, None

        if user.is_locked():
            return user, None, None

        if user.is_deleted():
            return user, None, None

        password_matches = await self._crypt.compare_hashes(
            password.to_raw(), user.hashed_password.to_raw()
        )

        if not password_matches:
            updated_user = user.record_failed_login_attempt(
                self.MAX_FAILED_ATTEMPTS,
                self.LOCKOUT_DURATION_MINUTES,
            )
            await self._user_repo.update(updated_user)
            self._uow.register(updated_user)
            return updated_user, None, None

        user = user.record_successful_login()
        await self._user_repo.update(user)
        self._uow.register(user)

        session, raw_refresh_token = self._build_session(user, device_info or DeviceInfo())
        return user, session, raw_refresh_token

    def _build_session(self, user: User, device_info: DeviceInfo) -> tuple[SessionAggregate, str]:
        session = SessionAggregate.create(
            user_id=user.id,
            device_info=device_info,
            session_expire_seconds=self.SESSION_EXPIRE_SECONDS,
        )
        raw_refresh_token = secrets.token_urlsafe(32)
        session = session.add_refresh_token(
            RefreshToken(
                token_hash=TokenHash.from_raw(raw_refresh_token),
                expires_at=datetime.now(UTC) + timedelta(seconds=self.REFRESH_TOKEN_EXPIRE_SECONDS),
            )
        )
        return session, raw_refresh_token

    async def start_session(
        self, user: User, device_info: DeviceInfo
    ) -> tuple[SessionAggregate, str]:
        """Create and persist a session for an already-authenticated user.

        Used by the second-factor step, where the password was checked in an earlier request.
        """
        session, raw_refresh_token = self._build_session(user, device_info)
        await self.persist_session(session)
        return session, raw_refresh_token

    async def persist_session(self, session: SessionAggregate) -> None:
        await self._session_repo.add(session)
        self._uow.register(session)

    async def refresh_session(
        self,
        refresh_token_str: str,
    ) -> tuple[SessionAggregate, User, str]:
        """Exchange a refresh token for a renewed session and a *new* refresh token.

        Rotation, not reuse: the presented token is revoked and replaced. Presenting a token
        that is already revoked while its session is still live means the token leaked and is
        being replayed, so the whole session is killed rather than merely refused.
        """
        token_hash = TokenHash.from_raw(refresh_token_str)

        session = await self._session_repo.acquire_by_token_hash(token_hash.to_raw())
        if not session or session.is_expired():
            raise InvalidCredentialsError()

        presented = session.find_refresh_token(token_hash)
        if presented is None:
            raise InvalidCredentialsError()

        if not presented.is_valid():
            # Replay of a token we already rotated away. Anyone still holding a live token
            # for this session is now suspect, so the session goes.
            revoked = session.revoke()
            await self._session_repo.update(revoked)
            self._uow.register(revoked)
            raise RefreshTokenReuseError()

        user = await self._user_repo.acquire_by_id(session.user_id)

        if user is None or user.is_deleted():
            raise InvalidCredentialsError()

        if user.is_locked():
            raise AccountLockedError(str(user.id.to_raw()))

        raw_refresh_token = secrets.token_urlsafe(32)
        refreshed_session = (
            session.revoke_token(presented.id)
            .add_refresh_token(
                RefreshToken(
                    token_hash=TokenHash.from_raw(raw_refresh_token),
                    expires_at=datetime.now(UTC)
                    + timedelta(seconds=self.REFRESH_TOKEN_EXPIRE_SECONDS),
                )
            )
            .refresh(self.SESSION_EXPIRE_SECONDS)
        )
        await self._session_repo.update(refreshed_session)
        self._uow.register(refreshed_session)

        return refreshed_session, user, raw_refresh_token

    async def revoke_session(self, session_id: UUID, user_id: UserID) -> SessionAggregate | None:
        session = await self._session_repo.acquire_by_session_id(session_id)
        if session and session.user_id == user_id:
            revoked_session = session.revoke()
            await self._session_repo.update(revoked_session)
            self._uow.register(revoked_session)
            return revoked_session
        return None

    async def revoke_all_sessions(self, user_id: UserID) -> list[SessionAggregate]:
        sessions = await self._session_repo.acquire_by_user_id(user_id)
        revoked_sessions = [session.revoke() for session in sessions]
        for revoked_session in revoked_sessions:
            await self._session_repo.update(revoked_session)
            self._uow.register(revoked_session)
        return revoked_sessions

    async def get_user_sessions(self, user_id: UserID) -> list[SessionAggregate]:
        return await self._session_repo.acquire_by_user_id(user_id)

    async def update_session(self, session: SessionAggregate) -> None:
        await self._session_repo.update(session)
        self._uow.register(session)

    async def verify_email(self, token: str) -> User:
        """Verify an address from the emailed token alone.

        The token identifies the user, so the link works for someone who is not (and cannot
        yet be) signed in — which is the whole point of a verification email.
        """
        user = await self._user_repo.acquire_by_verification_token(TokenHash.from_raw(token))
        if user is None or not user.verify_email(token):
            raise InvalidTokenError('Invalid or expired verification token')

        verified_user = user.mark_email_verified()
        await self._user_repo.update(verified_user)
        self._uow.register(verified_user)
        return verified_user

    async def request_password_reset(self, email: Email) -> User | None:
        user = await self._user_repo.acquire_by_email(email)
        if user is None:
            return None

        updated_user = user.request_password_reset()
        await self._user_repo.update(updated_user)
        self._uow.register(updated_user)
        return updated_user

    async def reset_password(self, token: str, new_password: PlainPassword) -> User:
        """Complete a password reset from the emailed token alone.

        The caller no longer supplies a user id: taking one from an unauthenticated request
        made the endpoint impossible to drive from an email link, and pointless as a check.
        The token's validity is enforced by `User.reset_password`.
        """
        user = await self._user_repo.acquire_by_reset_token(TokenHash.from_raw(token))
        if user is None:
            raise InvalidTokenError('Invalid or expired password reset token')

        hashed_password = await self._crypt.hash(new_password.to_raw())
        new_hashed_password = HashedPassword(hashed_password)

        updated_user = user.reset_password(token, new_hashed_password)
        await self._user_repo.update(updated_user)
        self._uow.register(updated_user)

        _ = await self.revoke_all_sessions(user.id)

        return updated_user

    async def change_password(
        self,
        user: User,
        old_password: PlainPassword,
        new_password: PlainPassword,
    ) -> User:
        hashed_password = await self._crypt.hash(new_password.to_raw())
        new_hashed_password = HashedPassword(hashed_password)

        updated_user = await user.change_password(old_password, new_hashed_password, self._crypt)
        await self._user_repo.update(updated_user)
        self._uow.register(updated_user)

        _ = await self.revoke_all_sessions(user.id)

        return updated_user

    async def delete_user(self, user_id: UserID) -> User:
        user = await self._user_repo.acquire_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id.to_raw()))

        if user.is_deleted():
            return user

        _ = await self.revoke_all_sessions(user_id)
        deleted_user = user.delete()
        await self._user_repo.update(deleted_user)
        self._uow.register(deleted_user)
        return deleted_user

    async def get_user_by_id(self, user_id: UserID) -> User:
        user = await self._user_repo.acquire_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id.to_raw()))
        if user.is_deleted():
            raise UserIsDeletedError(user_id.to_raw())
        return user

    async def update_user(
        self,
        user: User,
        username: Username | None = None,
        email: Email | None = None,
    ) -> User:
        if user.is_deleted():
            raise UserIsDeletedError(user.id.to_raw())

        updated = user

        if username is not None and username.to_raw() != user.username.to_raw():
            username_exists = await self._user_repo.check_username_exists(username)
            if username_exists:
                raise UsernameAlreadyExistsError(username.to_raw())
            updated = updated.update_username(username)

        if email is not None and email.to_raw() != user.email.to_raw():
            email_exists = await self._user_repo.check_email_exists(email)
            if email_exists:
                raise EmailAlreadyExistsError(email.to_raw())
            updated = updated.update_email(email)

        await self._user_repo.update(updated)
        self._uow.register(updated)
        return updated
