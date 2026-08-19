import pytest
from uuid import uuid4
from datetime import UTC, datetime, timedelta

from domain.user.value_objects import (
    AccountLockInfo,
    Email,
    HashedPassword,
    PlainPassword,
    SecureToken,
    TokenHash,
    TwoFactorSecret,
    UserID,
    Username,
)
from domain.user.entities.user import User
from domain.user.entities.session import SessionAggregate, DeviceInfo, RefreshToken


class TestUserID:
    def test_create_valid_user_id(self):
        user_id = UserID(uuid4())
        assert user_id.value is not None

    def test_create_none_user_id(self):
        from domain.user.value_objects.user_id import WrongUserIDError
        with pytest.raises(WrongUserIDError):
            UserID(None)


class TestUsername:
    def test_create_valid_username(self):
        username = Username("testuser")
        assert username.to_raw() == "testuser"

    def test_create_empty_username(self):
        from domain.user.value_objects.username import EmptyUsernameError
        with pytest.raises(EmptyUsernameError):
            Username("")

    def test_create_long_username(self):
        from domain.user.value_objects.username import TooLongUsernameError
        with pytest.raises(TooLongUsernameError):
            Username("a" * 50)


class TestEmail:
    def test_create_valid_email(self):
        email = Email("test@example.com")
        assert email.to_raw() == "test@example.com"

    def test_create_none_email(self):
        email = Email(None)
        assert email.to_raw() is None

    def test_create_invalid_email(self):
        from domain.user.value_objects.email import InvalidEmailFormatError
        with pytest.raises(InvalidEmailFormatError):
            Email("invalid-email")


class TestPlainPassword:
    def test_create_valid_password(self):
        password = PlainPassword("Test@1234")
        assert password.to_raw() == "Test@1234"

    def test_create_weak_password(self):
        from domain.user.value_objects.password import PasswordTooWeakError
        with pytest.raises(PasswordTooWeakError):
            PlainPassword("weakweakwe")

    def test_create_short_password(self):
        from domain.user.value_objects.password import PasswordTooShortError
        with pytest.raises(PasswordTooShortError):
            PlainPassword("Test1@")


class TestSecureToken:
    def test_create_token(self):
        token = SecureToken.create(expires_in_hours=1)
        assert len(token.value) >= 16
        assert token.is_valid()

    def test_create_hex_token(self):
        token = SecureToken.create_hex(expires_in_hours=1)
        assert len(token.value) >= 32

    def test_token_expiry(self):
        token = SecureToken.create(expires_in_hours=0)
        assert not token.is_valid()


class TestTwoFactorSecret:
    def test_create_secret(self):
        secret = TwoFactorSecret.create('JBSWY3DPEHPK3PXP')
        assert secret.secret == 'JBSWY3DPEHPK3PXP'
        assert len(secret.backup_codes) == 10

    def test_enable_2fa(self):
        secret = TwoFactorSecret.create('JBSWY3DPEHPK3PXP')
        enabled = secret.enable()
        assert enabled.enabled_at is not None

    def test_backup_code_verification(self):
        secret = TwoFactorSecret.create('JBSWY3DPEHPK3PXP')
        code = secret.backup_codes[0]
        consumed = secret.consume_backup_code(code)
        assert consumed is not None
        assert code not in consumed.backup_codes
        assert len(consumed.backup_codes) == len(secret.backup_codes) - 1

    def test_backup_code_cannot_be_replayed(self):
        secret = TwoFactorSecret.create('JBSWY3DPEHPK3PXP')
        code = secret.backup_codes[0]
        consumed = secret.consume_backup_code(code)
        assert consumed.consume_backup_code(code) is None

    def test_unknown_backup_code_returns_none(self):
        secret = TwoFactorSecret.create('JBSWY3DPEHPK3PXP')
        assert secret.consume_backup_code('not-a-real-code') is None


class TestTwoFactorAuth:
    def test_generate_secret_returns_base32(self):
        from infrastructure.two_factor import TwoFactorAuth

        secret = TwoFactorAuth().generate_secret()
        assert len(secret) >= 16

    def test_get_provisioning_uri(self):
        from infrastructure.two_factor import TwoFactorAuth

        uri = TwoFactorAuth().get_provisioning_uri('JBSWY3DPEHPK3PXP', 'testuser')
        assert "otpauth://totp/" in uri
        assert "testuser" in uri

    def test_verify_code_accepts_current_totp(self):
        import pyotp
        from infrastructure.two_factor import TwoFactorAuth

        secret = pyotp.random_base32()
        code = pyotp.TOTP(secret).now()
        assert TwoFactorAuth().verify_code(secret, code) is True

    def test_verify_code_rejects_wrong_code(self):
        import pyotp
        from infrastructure.two_factor import TwoFactorAuth

        secret = pyotp.random_base32()
        assert TwoFactorAuth().verify_code(secret, '000000') is False


class TestAccountLockInfo:
    def test_create_default(self):
        lock = AccountLockInfo.create()
        assert not lock.is_locked_out()
        assert lock.failed_attempts == 0

    def test_record_failed_attempt(self):
        lock = AccountLockInfo.create()
        for _ in range(5):
            lock = lock.record_failed_attempt(max_attempts=5)
        assert lock.is_locked_out()

    def test_record_successful_login(self):
        lock = AccountLockInfo.create_locked("test", datetime.now(UTC) + timedelta(minutes=15))
        unlocked = lock.record_successful_login()
        assert not unlocked.is_locked_out()
        assert unlocked.failed_attempts == 0

    def test_unlock_after_timeout(self):
        lock = AccountLockInfo.create_locked("test", datetime.now(UTC) - timedelta(minutes=1))
        assert not lock.is_locked_out()


class TestUserAggregate:
    @pytest.fixture
    def valid_user_id(self):
        return UserID(uuid4())

    @pytest.fixture
    def valid_username(self):
        return Username("testuser")

    @pytest.fixture
    def valid_email(self):
        return Email("test@example.com")

    @pytest.fixture
    def hashed_password(self):
        return HashedPassword(b"hashed_password")

    def test_create_user(self, valid_user_id, valid_username, valid_email, hashed_password):
        user = User.create(
            user_id=valid_user_id,
            username=valid_username,
            email=valid_email,
            hashed_password=hashed_password,
            verification_token="test_token",
        )
        assert user.id == valid_user_id
        assert user.username == valid_username
        assert user.email == valid_email

    def test_user_is_immutable(self, valid_user_id, valid_username, valid_email, hashed_password):
        user = User.create(
            user_id=valid_user_id,
            username=valid_username,
            email=valid_email,
            hashed_password=hashed_password,
            verification_token="test_token",
        )
        updated_user = user.record_successful_login()
        assert updated_user is not user

    def test_record_failed_login(self, valid_user_id, valid_username, valid_email, hashed_password):
        user = User.create(
            user_id=valid_user_id,
            username=valid_username,
            email=valid_email,
            hashed_password=hashed_password,
            verification_token="test_token",
        )
        for _ in range(5):
            user = user.record_failed_login_attempt(max_attempts=5)
        assert user.is_locked()

    def test_email_verification(self, valid_user_id, valid_username, valid_email, hashed_password):
        user = User.create(
            user_id=valid_user_id,
            username=valid_username,
            email=valid_email,
            hashed_password=hashed_password,
            verification_token="test_token",
        )
        verified = user.mark_email_verified()
        assert verified.email_verification.is_verified

    def test_delete_user(self, valid_user_id, valid_username, valid_email, hashed_password):
        user = User.create(
            user_id=valid_user_id,
            username=valid_username,
            email=valid_email,
            hashed_password=hashed_password,
            verification_token="test_token",
        )
        deleted = user.delete()
        assert deleted.is_deleted()

    def test_enable_2fa(self, valid_user_id, valid_username, valid_email, hashed_password):
        from infrastructure.two_factor import TwoFactorAuth

        user = User.create(
            user_id=valid_user_id,
            username=valid_username,
            email=valid_email,
            hashed_password=hashed_password,
            verification_token="test_token",
        )
        enabled = user.enable_two_factor(TwoFactorAuth())
        assert enabled.two_factor_secret is not None
        assert enabled.two_factor_secret.enabled_at is not None

    def test_verify_two_factor_backup_code_is_consumed(
        self, valid_user_id, valid_username, valid_email, hashed_password,
    ):
        from infrastructure.two_factor import TwoFactorAuth

        two_factor = TwoFactorAuth()
        user = User.create(
            user_id=valid_user_id,
            username=valid_username,
            email=valid_email,
            hashed_password=hashed_password,
            verification_token="test_token",
        ).enable_two_factor(two_factor)
        code = user.two_factor_secret.backup_codes[0]

        success, updated = user.verify_two_factor(code, two_factor)
        assert success is True
        assert code not in updated.two_factor_secret.backup_codes

        # The same code must not verify again against the updated user.
        replay_success, _ = updated.verify_two_factor(code, two_factor)
        assert replay_success is False

    def test_password_reset(self, valid_user_id, valid_username, valid_email, hashed_password):
        user = User.create(
            user_id=valid_user_id,
            username=valid_username,
            email=valid_email,
            hashed_password=hashed_password,
            verification_token="test_token",
        )
        reset_user = user.request_password_reset()
        assert reset_user.password_reset_token is not None
        
        new_password = HashedPassword(b"new_hashed")
        reset_complete = reset_user.reset_password(
            reset_user.password_reset_token.token,
            new_password
        )
        assert reset_complete.hashed_password == new_password
        assert reset_complete.password_reset_token.is_used


class TestSessionAggregate:
    def test_create_session(self):
        session = SessionAggregate.create(
            user_id=UserID(uuid4()),
            device_info=DeviceInfo(user_agent="test", ip_address="127.0.0.1"),
        )
        assert session.session_id is not None
        assert session.is_valid()

    def test_session_is_immutable(self):
        session = SessionAggregate.create(
            user_id=UserID(uuid4()),
            device_info=DeviceInfo(),
        )
        revoked = session.revoke()
        assert revoked is not session
        assert session.is_valid()
        assert not revoked.is_valid()

    def test_add_refresh_token(self):
        session = SessionAggregate.create(
            user_id=UserID(uuid4()),
            device_info=DeviceInfo(),
        )
        token = RefreshToken(
            token_hash=TokenHash(b"token_hash"),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        updated = session.add_refresh_token(token)
        assert len(updated.refresh_tokens) == 1
        assert len(session.refresh_tokens) == 0

    def test_refresh_session(self):
        session = SessionAggregate.create(
            user_id=UserID(uuid4()),
            device_info=DeviceInfo(),
            session_expire_seconds=60 * 60 * 24 * 30,
        )
        refreshed = session.refresh(60 * 60 * 24 * 30)
        assert refreshed is not session
        assert session.expires_at != refreshed.expires_at

    def test_revoke_token(self):
        session = SessionAggregate.create(
            user_id=UserID(uuid4()),
            device_info=DeviceInfo(),
        )
        token = RefreshToken(
            id=uuid4(),
            token_hash=TokenHash(b"token_hash"),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session = session.add_refresh_token(token)
        token_id = session.refresh_tokens[0].id
        revoked = session.revoke_token(token_id)
        assert revoked.refresh_tokens[0].is_revoked


class TestEntityIdentityEquality:
    def _user(self, user_id: UserID | None = None) -> User:
        return User.create(
            user_id=user_id or UserID(uuid4()),
            username=Username('testuser'),
            email=Email('test@example.com'),
            hashed_password=HashedPassword(b'hashed'),
            verification_token='test_token',
        )

    def test_same_id_different_state_is_equal(self):
        user = self._user()
        mutated = user.record_successful_login()

        assert mutated is not user
        assert mutated == user
        assert hash(mutated) == hash(user)

    def test_different_id_is_not_equal(self):
        assert self._user() != self._user()

    def test_entity_is_usable_as_set_member(self):
        user = self._user()
        mutated = user.record_successful_login()
        assert {user, mutated} == {user}

    def test_not_equal_to_unrelated_object(self):
        assert self._user() != 'not-a-user'


class TestValueObjects:
    def test_user_id_to_raw(self):
        user_id = UserID(uuid4())
        assert user_id.to_raw() is not None

    def test_username_to_raw(self):
        username = Username("testuser")
        assert username.to_raw() == "testuser"

    def test_email_to_raw(self):
        email = Email("test@example.com")
        assert email.to_raw() == "test@example.com"

    def test_plain_password_to_raw(self):
        password = PlainPassword("Test@1234")
        assert password.to_raw() == "Test@1234"

    def test_hashed_password_to_raw(self):
        password = HashedPassword(b"hashed")
        assert password.to_raw() == b"hashed"
