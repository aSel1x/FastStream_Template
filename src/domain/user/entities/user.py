from dataclasses import dataclass, field
from typing import Self, override

from domain.common.entity import BaseEntity
from domain.common.event_dispatcher import DomainEventDispatcher
from domain.user.events import (
    AccountLockedEvent,
    AccountUnlockedEvent,
    EmailVerifiedEvent,
    EmailVerificationRequestedEvent,
    PasswordResetCompletedEvent,
    PasswordResetRequestedEvent,
    TwoFactorEnabledEvent,
    TwoFactorDisabledEvent,
    UserAuthenticatedEvent,
    UserCreatedEvent,
    PasswordChangedEvent,
    UserDeletedEvent,
    UserProfileUpdatedEvent,
    UserRoleAssignedEvent,
    UserRoleRevokedEvent,
)
from domain.user.exceptions import InvalidCredentialsError, InvalidTokenError
from domain.user.interfaces.acl.crypt import CryptInterface
from domain.user.interfaces.acl.two_factor import TwoFactorInterface
from domain.user.value_objects import (
    AccountLockInfo,
    DeletionTime,
    Email,
    EmailVerification,
    HashedPassword,
    PasswordResetToken,
    PlainPassword,
    RoleID,
    SecureToken,
    TwoFactorSecret,
    UserID,
    Username,
)


@dataclass(frozen=True, kw_only=True, eq=False)
class User(DomainEventDispatcher, BaseEntity):
    id: UserID
    username: Username
    email: Email
    hashed_password: HashedPassword
    deleted_at: DeletionTime = field(default=DeletionTime.create_not_deleted())
    account_lock: AccountLockInfo = field(default_factory=AccountLockInfo.create)
    email_verification: EmailVerification = field(
        default_factory=lambda: EmailVerification.create_unverified(SecureToken.create_hex().value)
    )
    password_reset_token: PasswordResetToken | None = field(default=None)
    two_factor_secret: TwoFactorSecret | None = field(default=None)

    @override
    def _identity(self) -> object:
        return self.id

    @classmethod
    def create(
        cls,
        user_id: UserID,
        username: Username,
        email: Email,
        hashed_password: HashedPassword,
        verification_token: str,
    ) -> Self:
        user = cls(
            id=user_id,
            username=username,
            email=email,
            hashed_password=hashed_password,
            email_verification=EmailVerification.create_unverified(verification_token),
        )
        email_raw = user.email.to_raw()
        user._record_event(
            UserCreatedEvent(
                user_id=user.id.to_raw(),
                username=user.username.to_raw(),
                email=email_raw,
            )
        )
        user._record_event(
            EmailVerificationRequestedEvent(
                user_id=user.id.to_raw(),
                email=email_raw or '',
                verification_token=verification_token,
            )
        )
        return user

    def is_deleted(self) -> bool:
        return self.deleted_at.is_deleted()

    def is_locked(self) -> bool:
        return self.account_lock.is_locked_out()

    def has_two_factor(self) -> bool:
        return self.two_factor_secret is not None and self.two_factor_secret.enabled_at is not None

    async def verify_password(self, plain_password: PlainPassword, crypt: CryptInterface) -> bool:
        return await crypt.compare_hashes(plain_password.to_raw(), self.hashed_password.to_raw())

    def verify_two_factor(self, code: str, two_factor: TwoFactorInterface) -> tuple[bool, Self]:
        """Verify a TOTP or backup code. A matched backup code is consumed (returns a new User)."""
        if not self.two_factor_secret or not self.two_factor_secret.enabled_at:
            return False, self
        if two_factor.verify_code(self.two_factor_secret.secret, code):
            return True, self
        consumed = self.two_factor_secret.consume_backup_code(code)
        if consumed is not None:
            return True, self._with(two_factor_secret=consumed)
        return False, self

    def record_failed_login_attempt(
        self, 
        max_attempts: int = 5, 
        lockout_duration_minutes: int = 15
    ) -> Self:
        new_lock_info = self.account_lock.record_failed_attempt(max_attempts, lockout_duration_minutes)
        new_user = self._with(account_lock=new_lock_info)
        if new_lock_info.is_locked and not self.account_lock.is_locked:
            new_user._record_event(AccountLockedEvent(
                user_id=self.id.to_raw(),
                reason='Too many failed login attempts',
                locked_until=new_lock_info.lock_until,
            ))
        return new_user

    def record_successful_login(self) -> Self:
        new_lock_info = self.account_lock.record_successful_login()
        user = self._with(account_lock=new_lock_info)
        user._record_event(UserAuthenticatedEvent(
            user_id=self.id.to_raw(),
            username=self.username.to_raw(),
        ))
        return user

    def unlock(self) -> Self:
        new_lock_info = self.account_lock.unlock()
        user = self._with(account_lock=new_lock_info)
        user._record_event(AccountUnlockedEvent(user_id=self.id.to_raw()))
        return user

    def lock(self, reason: str) -> Self:
        new_lock_info = AccountLockInfo.create_locked(reason)
        user = self._with(account_lock=new_lock_info)
        user._record_event(AccountLockedEvent(
            user_id=self.id.to_raw(),
            reason=reason,
            locked_until=None,
        ))
        return user

    def verify_email(self, token: str) -> bool:
        return self.email_verification.verify(token)

    def mark_email_verified(self) -> Self:
        verified = self.email_verification.mark_verified()
        user = self._with(email_verification=verified)
        user._record_event(EmailVerifiedEvent(
            user_id=self.id.to_raw(),
            email=self.email.to_raw() or '',
        ))
        return user

    def request_password_reset(self, expires_in_hours: int = 1) -> Self:
        secure_token = SecureToken.create(expires_in_hours=expires_in_hours)
        reset_token = PasswordResetToken(
            token=secure_token.value,
            created_at=secure_token.created_at,
            expires_at=secure_token.expires_at,
        )
        user = self._with(password_reset_token=reset_token)
        user._record_event(PasswordResetRequestedEvent(
            user_id=self.id.to_raw(),
            email=self.email.to_raw() or '',
            reset_token=secure_token.value,
        ))
        return user

    def reset_password(self, token: str, new_hashed_password: HashedPassword) -> Self:
        if not self.password_reset_token or not self.password_reset_token.is_valid():
            raise InvalidTokenError('Invalid or expired password reset token')
        if self.password_reset_token.token != token:
            raise InvalidTokenError('Invalid password reset token')

        user = self._with(
            hashed_password=new_hashed_password,
            account_lock=self.account_lock.unlock(),
            password_reset_token=self.password_reset_token.mark_used(),
        )
        user._record_event(PasswordResetCompletedEvent(user_id=self.id.to_raw()))
        return user

    def enable_two_factor(self, two_factor: TwoFactorInterface) -> Self:
        secret = TwoFactorSecret.create(two_factor.generate_secret())
        enabled_secret = secret.enable()
        user = self._with(two_factor_secret=enabled_secret)
        user._record_event(TwoFactorEnabledEvent(
            user_id=self.id.to_raw(),
            backup_codes=secret.backup_codes,
        ))
        return user

    def disable_two_factor(self) -> Self:
        user = self._with(two_factor_secret=None)
        user._record_event(TwoFactorDisabledEvent(user_id=self.id.to_raw()))
        return user

    def update_username(self, new_username: Username) -> Self:
        if new_username.to_raw() != self.username.to_raw():
            user = self._with(username=new_username)
            user._record_event(
                UserProfileUpdatedEvent(
                    user_id=self.id.to_raw(),
                    updated_fields=('username',),
                )
            )
            return user
        return self

    def update_email(self, new_email: Email) -> Self:
        if new_email.to_raw() != self.email.to_raw():
            secure_token = SecureToken.create_hex(expires_in_hours=24)
            user = self._with(
                email=new_email,
                email_verification=EmailVerification.create_unverified(secure_token.value),
            )
            user._record_event(
                UserProfileUpdatedEvent(
                    user_id=self.id.to_raw(),
                    updated_fields=('email',),
                )
            )
            user._record_event(EmailVerificationRequestedEvent(
                user_id=self.id.to_raw(),
                email=new_email.to_raw() or '',
                verification_token=secure_token.value,
            ))
            return user
        return self

    def delete(self) -> Self:
        if not self.is_deleted():
            user = self._with(deleted_at=DeletionTime.create_deleted())
            user._record_event(UserDeletedEvent(user_id=self.id.to_raw()))
            return user
        return self

    def assign_role(self, role_id: RoleID, assigned_by: UserID | None = None) -> Self:
        user = self._with()
        user._record_event(UserRoleAssignedEvent(
            user_id=self.id.to_raw(),
            role_id=role_id.to_raw(),
            assigned_by=assigned_by.to_raw() if assigned_by else None,
        ))
        return user

    def revoke_role(self, role_id: RoleID) -> Self:
        user = self._with()
        user._record_event(UserRoleRevokedEvent(
            user_id=self.id.to_raw(),
            role_id=role_id.to_raw(),
            revoked_by=None,
        ))
        return user

    async def change_password(
        self, old_password: PlainPassword, new_password: HashedPassword, crypt: CryptInterface
    ) -> Self:
        if not await self.verify_password(old_password, crypt):
            raise InvalidCredentialsError('Invalid current password')
        user = self._with(
            hashed_password=new_password,
            account_lock=self.account_lock.unlock(),
            password_reset_token=None,
        )
        user._record_event(PasswordChangedEvent(user_id=self.id.to_raw()))
        return user