from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pyotp
import pytest

from domain.user.entities.rbac import Permission, Role
from domain.user.entities.session import DeviceInfo, SessionAggregate
from domain.user.entities.user import User
from domain.user.interfaces.persistence.readers import SessionReadDTO
from domain.user.value_objects import (
    Email,
    HashedPassword,
    RoleName,
    TwoFactorSecret,
    UserID,
    Username,
)


def _make_user(**overrides: object) -> User:
    defaults: dict[str, object] = dict(
        id=UserID(uuid4()),
        username=Username("testuser"),
        email=Email("test@example.com"),
        hashed_password=HashedPassword(b"hashed"),
    )
    defaults.update(overrides)
    return User(**defaults)


@pytest.fixture
def mock_uow():
    uow = MagicMock()
    uow.add_events = MagicMock()
    uow.commit = AsyncMock()
    return uow


class TestDeleteMeUseCase:
    @pytest.mark.asyncio
    async def test_deletes_user_and_commits(self, mock_uow):
        from application.user.commands.delete_me import DeleteMeUseCase

        user = _make_user()
        deleted_user = user.delete()
        user_service = MagicMock()
        user_service.delete_user = AsyncMock(return_value=deleted_user)

        use_case = DeleteMeUseCase(user_service=user_service, uow=mock_uow)
        await use_case(user.id.to_raw())

        user_service.delete_user.assert_awaited_once_with(user.id)
        mock_uow.add_events.assert_called_once()
        mock_uow.commit.assert_awaited_once()


class TestEnable2FAUseCase:
    @pytest.mark.asyncio
    async def test_enable_returns_secret_and_backup_codes(self, mock_uow):
        from application.user.commands.manage_2fa import Enable2FAUseCase
        from infrastructure.two_factor import TwoFactorAuth

        user = _make_user()
        user_service = MagicMock()
        user_service.get_user_by_id = AsyncMock(return_value=user)
        user_service.update_user = AsyncMock()

        use_case = Enable2FAUseCase(
            user_service=user_service, two_factor=TwoFactorAuth(), uow=mock_uow
        )
        result = await use_case(user.id.to_raw())

        assert result.secret
        assert len(result.backup_codes) == 10
        assert "otpauth://" in result.provisioning_uri
        user_service.update_user.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()


class TestDisable2FAUseCase:
    @pytest.mark.asyncio
    async def test_disable_with_correct_password(self, mock_uow):
        from application.user.commands.manage_2fa import Disable2FAUseCase
        from infrastructure.two_factor import TwoFactorAuth

        user = _make_user().enable_two_factor(TwoFactorAuth())
        user_service = MagicMock()
        user_service.get_user_by_id = AsyncMock(return_value=user)
        user_service.update_user = AsyncMock()
        crypt = AsyncMock()
        crypt.compare_hashes = AsyncMock(return_value=True)

        use_case = Disable2FAUseCase(user_service=user_service, crypt=crypt, uow=mock_uow)
        await use_case(user.id.to_raw(), "Correct@1234")

        updated = user_service.update_user.await_args.args[0]
        assert updated.has_two_factor() is False
        mock_uow.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disable_with_wrong_password_raises(self, mock_uow):
        from application.user.commands.manage_2fa import Disable2FAUseCase
        from domain.user.exceptions import InvalidCredentialsError
        from infrastructure.two_factor import TwoFactorAuth

        user = _make_user().enable_two_factor(TwoFactorAuth())
        user_service = MagicMock()
        user_service.get_user_by_id = AsyncMock(return_value=user)
        crypt = AsyncMock()
        crypt.compare_hashes = AsyncMock(return_value=False)

        use_case = Disable2FAUseCase(user_service=user_service, crypt=crypt, uow=mock_uow)

        with pytest.raises(InvalidCredentialsError):
            await use_case(user.id.to_raw(), "Wrong@1234")

        mock_uow.commit.assert_not_awaited()


class TestVerify2FAUseCase:
    def _use_case(self, user: User, mock_uow):
        from application.user.commands.manage_2fa import Verify2FAUseCase
        from infrastructure.two_factor import TwoFactorAuth

        repo = AsyncMock()
        repo.acquire_by_id = AsyncMock(return_value=user)
        repo.update = AsyncMock()
        return Verify2FAUseCase(user_repo=repo, two_factor=TwoFactorAuth(), uow=mock_uow), repo

    @pytest.mark.asyncio
    async def test_verify_valid_totp_code(self, mock_uow):
        from application.user.commands.manage_2fa import Verify2FAInput

        secret = TwoFactorSecret.create(pyotp.random_base32()).enable()
        user = _make_user(two_factor_secret=secret)
        use_case, repo = self._use_case(user, mock_uow)

        code = pyotp.TOTP(secret.secret).now()
        result = await use_case(user.id.to_raw(), Verify2FAInput(code=code))

        assert result.success is True
        repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_backup_code_is_consumed_and_cannot_be_replayed(self, mock_uow):
        from application.user.commands.manage_2fa import Verify2FAInput, Verify2FAUseCase
        from infrastructure.two_factor import TwoFactorAuth

        secret = TwoFactorSecret.create(pyotp.random_base32()).enable()
        user = _make_user(two_factor_secret=secret)
        used_code = secret.backup_codes[0]

        repo = AsyncMock()
        repo.acquire_by_id = AsyncMock(return_value=user)
        updated_user: list[User] = []
        repo.update = AsyncMock(side_effect=lambda u: updated_user.append(u))
        use_case = Verify2FAUseCase(user_repo=repo, two_factor=TwoFactorAuth(), uow=mock_uow)

        result = await use_case(user.id.to_raw(), Verify2FAInput(code=used_code))

        assert result.success is True
        repo.update.assert_awaited_once()
        assert used_code not in updated_user[0].two_factor_secret.backup_codes

        # Replaying the SAME code against the now-persisted (updated) user must fail.
        repo.acquire_by_id = AsyncMock(return_value=updated_user[0])
        replay_result = await use_case(user.id.to_raw(), Verify2FAInput(code=used_code))
        assert replay_result.success is False

    @pytest.mark.asyncio
    async def test_verify_wrong_code_fails(self, mock_uow):
        from application.user.commands.manage_2fa import Verify2FAInput

        secret = TwoFactorSecret.create(pyotp.random_base32()).enable()
        user = _make_user(two_factor_secret=secret)
        use_case, repo = self._use_case(user, mock_uow)

        result = await use_case(user.id.to_raw(), Verify2FAInput(code="000000"))

        assert result.success is False
        repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_without_2fa_enabled_fails(self, mock_uow):
        from application.user.commands.manage_2fa import Verify2FAInput

        user = _make_user(two_factor_secret=None)
        use_case, repo = self._use_case(user, mock_uow)

        result = await use_case(user.id.to_raw(), Verify2FAInput(code="000000"))

        assert result.success is False
        repo.update.assert_not_awaited()


class TestRevokeSessionUseCase:
    @pytest.mark.asyncio
    async def test_revokes_owned_session(self, mock_uow):
        from application.user.commands.manage_sessions import RevokeSessionUseCase

        user_id = UserID(uuid4())
        session = SessionAggregate.create(user_id=user_id, device_info=DeviceInfo()).revoke()
        user_service = MagicMock()
        user_service.revoke_session = AsyncMock(return_value=session)

        use_case = RevokeSessionUseCase(user_service=user_service, uow=mock_uow)
        await use_case(user_id.to_raw(), str(session.session_id))

        mock_uow.add_events.assert_called_once()
        mock_uow.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_revoking_unowned_session_is_a_noop(self, mock_uow):
        from application.user.commands.manage_sessions import RevokeSessionUseCase

        user_service = MagicMock()
        user_service.revoke_session = AsyncMock(return_value=None)

        use_case = RevokeSessionUseCase(user_service=user_service, uow=mock_uow)
        await use_case(uuid4(), str(uuid4()))

        mock_uow.add_events.assert_not_called()
        mock_uow.commit.assert_not_awaited()


class TestRevokeAllSessionsUseCase:
    @pytest.mark.asyncio
    async def test_revokes_every_session_and_commits_once(self, mock_uow):
        from application.user.commands.manage_sessions import RevokeAllSessionsUseCase

        user_id = UserID(uuid4())
        sessions = [
            SessionAggregate.create(user_id=user_id, device_info=DeviceInfo()).revoke()
            for _ in range(3)
        ]
        user_service = MagicMock()
        user_service.revoke_all_sessions = AsyncMock(return_value=sessions)
        hydra = MagicMock()
        hydra.revoke_consent_sessions = AsyncMock()
        hydra.revoke_login_sessions = AsyncMock()

        use_case = RevokeAllSessionsUseCase(user_service=user_service, hydra=hydra, uow=mock_uow)
        await use_case(user_id.to_raw())

        assert mock_uow.add_events.call_count == 3
        mock_uow.commit.assert_awaited_once()
        hydra.revoke_consent_sessions.assert_awaited_once_with(str(user_id.to_raw()))
        hydra.revoke_login_sessions.assert_awaited_once_with(str(user_id.to_raw()))


class TestGetUserSessionsUseCase:
    @pytest.mark.asyncio
    async def test_paginates_sessions(self):
        from application.user.queries.manage_sessions import GetUserSessionsUseCase

        now = datetime.now(UTC)
        sessions = [
            SessionReadDTO(
                session_id=uuid4(),
                created_at=now,
                expires_at=now + timedelta(days=1),
                is_revoked=False,
                device_info=DeviceInfo(),
            )
            for _ in range(5)
        ]
        reader = AsyncMock()
        reader.get_by_user_id = AsyncMock(return_value=sessions)

        use_case = GetUserSessionsUseCase(session_reader=reader)
        page = await use_case(uuid4(), limit=2, offset=1)

        assert len(page.sessions) == 2
        assert page.total == 5
        assert page.has_more is True

    @pytest.mark.asyncio
    async def test_last_page_has_no_more(self):
        from application.user.queries.manage_sessions import GetUserSessionsUseCase

        now = datetime.now(UTC)
        sessions = [
            SessionReadDTO(
                session_id=uuid4(),
                created_at=now,
                expires_at=now + timedelta(days=1),
                is_revoked=False,
                device_info=DeviceInfo(),
            )
            for _ in range(3)
        ]
        reader = AsyncMock()
        reader.get_by_user_id = AsyncMock(return_value=sessions)

        use_case = GetUserSessionsUseCase(session_reader=reader)
        page = await use_case(uuid4(), limit=20, offset=0)

        assert page.has_more is False


class TestVerifyEmailUseCase:
    @pytest.mark.asyncio
    async def test_verifies_with_correct_token(self, mock_uow):
        from application.user.commands.verify_email import VerifyEmailInput, VerifyEmailUseCase

        user = _make_user()
        verified_user = user.mark_email_verified()
        user_service = MagicMock()
        user_service.verify_email = AsyncMock(return_value=verified_user)

        use_case = VerifyEmailUseCase(user_service=user_service, uow=mock_uow)
        result = await use_case(VerifyEmailInput(user_id=str(user.id.to_raw()), token="tok"))

        assert result.success is True
        mock_uow.commit.assert_awaited_once()


class TestRequestPasswordResetUseCase:
    @pytest.mark.asyncio
    async def test_always_reports_success_even_when_user_unknown(self, mock_uow):
        from application.user.commands.reset_password import (
            RequestPasswordResetInput,
            RequestPasswordResetUseCase,
        )

        user_service = MagicMock()
        user_service.request_password_reset = AsyncMock(return_value=None)
        rate_limiter = AsyncMock()
        rate_limiter.check = AsyncMock(return_value=(True, 10, None))

        use_case = RequestPasswordResetUseCase(
            user_service=user_service,
            uow=mock_uow,
            rate_limiter=rate_limiter,
        )
        result = await use_case(RequestPasswordResetInput(email="nobody@example.com"))

        assert result.success is True
        mock_uow.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rate_limited_raises(self, mock_uow):
        from application.common.exceptions import TooManyLoginAttemptsError
        from application.user.commands.reset_password import (
            RequestPasswordResetInput,
            RequestPasswordResetUseCase,
        )

        user_service = MagicMock()
        rate_limiter = AsyncMock()
        rate_limiter.check = AsyncMock(return_value=(False, 0, None))

        use_case = RequestPasswordResetUseCase(
            user_service=user_service,
            uow=mock_uow,
            rate_limiter=rate_limiter,
        )

        with pytest.raises(TooManyLoginAttemptsError):
            await use_case(RequestPasswordResetInput(email="a@example.com", ip_address="1.2.3.4"))

        user_service.request_password_reset.assert_not_called()


class TestResetPasswordUseCase:
    @pytest.mark.asyncio
    async def test_resets_password_and_commits(self, mock_uow):
        from application.user.commands.reset_password import (
            ResetPasswordInput,
            ResetPasswordUseCase,
        )

        user = _make_user()
        user_service = MagicMock()
        user_service.reset_password = AsyncMock(return_value=user)
        rate_limiter = AsyncMock()
        rate_limiter.check = AsyncMock(return_value=(True, 10, None))

        use_case = ResetPasswordUseCase(
            user_service=user_service, uow=mock_uow, rate_limiter=rate_limiter
        )
        result = await use_case(
            ResetPasswordInput(
                user_id=str(user.id.to_raw()),
                token="tok",
                new_password="New@1234",
            )
        )

        assert result.success is True
        mock_uow.commit.assert_awaited_once()


class TestUpdateProfileUseCase:
    @pytest.mark.asyncio
    async def test_returns_real_account_state_not_hardcoded(self, mock_uow):
        from application.user.commands.update_profile import (
            UpdateProfileInput,
            UpdateProfileUseCase,
        )
        from infrastructure.two_factor import TwoFactorAuth

        user = _make_user().mark_email_verified().enable_two_factor(TwoFactorAuth())
        updated = user.update_username(Username("newname"))
        user_service = MagicMock()
        user_service.get_user_by_id = AsyncMock(return_value=user)
        user_service.update_user = AsyncMock(return_value=updated)

        use_case = UpdateProfileUseCase(user_service=user_service, uow=mock_uow)
        result = await use_case(UpdateProfileInput(user_id=user.id.to_raw(), username="newname"))

        assert result.username == "newname"
        assert result.is_email_verified is True
        assert result.is_locked is False
        assert result.has_two_factor is True


class TestChangePasswordUseCase:
    @pytest.mark.asyncio
    async def test_changes_password_with_correct_old_password(self, mock_uow):
        from application.user.commands.change_password import (
            ChangePasswordInput,
            ChangePasswordUseCase,
        )

        user = _make_user()
        changed = user._with(hashed_password=HashedPassword(b"new-hash"))
        user_service = MagicMock()
        user_service.get_user_by_id = AsyncMock(return_value=user)
        user_service.change_password = AsyncMock(return_value=changed)

        use_case = ChangePasswordUseCase(user_service=user_service, uow=mock_uow)
        result = await use_case(
            ChangePasswordInput(
                user_id=user.id.to_raw(),
                old_password="Old@1234",
                new_password="New@1234",
            )
        )

        assert result.success is True
        user_service.change_password.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_wrong_old_password_propagates(self, mock_uow):
        from application.user.commands.change_password import (
            ChangePasswordInput,
            ChangePasswordUseCase,
        )
        from domain.user.exceptions import InvalidCredentialsError

        user = _make_user()
        user_service = MagicMock()
        user_service.get_user_by_id = AsyncMock(return_value=user)
        user_service.change_password = AsyncMock(side_effect=InvalidCredentialsError())

        use_case = ChangePasswordUseCase(user_service=user_service, uow=mock_uow)

        with pytest.raises(InvalidCredentialsError):
            await use_case(
                ChangePasswordInput(
                    user_id=user.id.to_raw(),
                    old_password="Wrong@1234",
                    new_password="New@1234",
                )
            )

        mock_uow.commit.assert_not_awaited()


class TestRefreshTokenUseCase:
    @pytest.mark.asyncio
    async def test_refreshes_session(self, mock_uow):
        from application.user.commands.refresh_token import RefreshTokenInput, RefreshTokenUseCase

        user = _make_user()
        session = SessionAggregate.create(user_id=user.id, device_info=DeviceInfo())
        user_service = MagicMock()
        user_service.refresh_session = AsyncMock(return_value=(session, user))

        use_case = RefreshTokenUseCase(user_service=user_service, uow=mock_uow)
        result = await use_case(RefreshTokenInput(refresh_token="raw-token"))

        assert result.user_id == user.id.to_raw()
        assert result.session_id == str(session.session_id)
        mock_uow.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_token_propagates(self, mock_uow):
        from application.user.commands.refresh_token import RefreshTokenInput, RefreshTokenUseCase
        from domain.user.exceptions import InvalidCredentialsError

        user_service = MagicMock()
        user_service.refresh_session = AsyncMock(side_effect=InvalidCredentialsError())

        use_case = RefreshTokenUseCase(user_service=user_service, uow=mock_uow)

        with pytest.raises(InvalidCredentialsError):
            await use_case(RefreshTokenInput(refresh_token="bogus"))

        mock_uow.commit.assert_not_awaited()


class TestDeleteRoleUseCase:
    @pytest.mark.asyncio
    async def test_deletes_role_and_commits(self, mock_uow):
        from application.user.commands.rbac import DeleteRoleInput, DeleteRoleUseCase

        role = Role.create(name=RoleName("temp"))
        deleted_role = role.delete()
        rbac_service = MagicMock()
        rbac_service.delete_role = AsyncMock(return_value=deleted_role)

        use_case = DeleteRoleUseCase(rbac_service=rbac_service, uow=mock_uow)
        await use_case(DeleteRoleInput(role_id=role.role_id.to_raw()))

        rbac_service.delete_role.assert_awaited_once_with(role.role_id)
        mock_uow.add_events.assert_called_once()
        mock_uow.commit.assert_awaited_once()


class TestAddPermissionToRoleUseCase:
    @pytest.mark.asyncio
    async def test_adds_permission_and_returns_role(self, mock_uow):
        from application.user.commands.rbac import (
            AddPermissionToRoleInput,
            AddPermissionToRoleUseCase,
        )

        role = Role.create(name=RoleName("editor"))
        updated_role = role.add_permission(Permission(name="posts.edit"))
        rbac_service = MagicMock()
        rbac_service.add_permission_to_role = AsyncMock(return_value=updated_role)

        use_case = AddPermissionToRoleUseCase(rbac_service=rbac_service, uow=mock_uow)
        result = await use_case(
            AddPermissionToRoleInput(role_id=role.role_id.to_raw(), permission_name="posts.edit")
        )

        assert result.permissions == ("posts.edit",)
        mock_uow.commit.assert_awaited_once()


class TestRemovePermissionFromRoleUseCase:
    @pytest.mark.asyncio
    async def test_removes_permission_and_returns_role(self, mock_uow):
        from application.user.commands.rbac import (
            RemovePermissionFromRoleInput,
            RemovePermissionFromRoleUseCase,
        )

        role = Role.create(name=RoleName("editor"), description=None)
        role = role.add_permission(Permission(name="posts.edit"))
        updated_role = role.remove_permission("posts.edit")
        rbac_service = MagicMock()
        rbac_service.remove_permission_from_role = AsyncMock(return_value=updated_role)

        use_case = RemovePermissionFromRoleUseCase(rbac_service=rbac_service, uow=mock_uow)
        result = await use_case(
            RemovePermissionFromRoleInput(
                role_id=role.role_id.to_raw(), permission_name="posts.edit"
            )
        )

        assert result.permissions == ()
        mock_uow.commit.assert_awaited_once()


class TestListPermissionsUseCase:
    @pytest.mark.asyncio
    async def test_lists_all_permissions(self):
        from application.user.queries.rbac import ListPermissionsUseCase

        permissions = [Permission(name="posts.edit"), Permission(name="posts.delete")]
        rbac_service = MagicMock()
        rbac_service.get_all_permissions = AsyncMock(return_value=permissions)

        use_case = ListPermissionsUseCase(rbac_service=rbac_service)
        result = await use_case()

        assert result == permissions
