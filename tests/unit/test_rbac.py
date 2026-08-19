import pytest
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, MagicMock, call
from datetime import datetime, UTC

from domain.user.value_objects import Email, HashedPassword, RoleID, RoleName, UserID, Username
from domain.user.entities.rbac import Permission, Role, UserRole
from domain.user.entities.user import User
from domain.user.events import (
    RoleCreatedEvent,
    RoleUpdatedEvent,
    RoleDeletedEvent,
    UserRoleAssignedEvent,
    UserRoleRevokedEvent,
)
from domain.user.exceptions import (
    RoleNotFoundError,
    RoleAlreadyExistsError,
    PermissionDeniedError,
    UserNotFoundError,
)


def _make_user(user_id: UUID | None = None) -> User:
    return User(
        id=UserID(user_id or uuid4()),
        username=Username('roleuser'),
        email=Email('roleuser@example.com'),
        hashed_password=HashedPassword(b'hashed'),
    )


class TestPermissionEntity:
    def test_create_with_valid_data(self):
        perm = Permission(name='edit_users', description='Can edit users')
        assert perm.name == 'edit_users'
        assert perm.description == 'Can edit users'

    def test_create_without_description(self):
        perm = Permission(name='view_users')
        assert perm.name == 'view_users'
        assert perm.description is None

    def test_immutability(self):
        perm = Permission(name='edit_users')
        with pytest.raises(AttributeError):
            perm.name = 'changed'

    def test_equality(self):
        perm1 = Permission(name='edit_users', description='Can edit')
        perm2 = Permission(name='edit_users', description='Can edit')
        perm3 = Permission(name='view_users')
        assert perm1 == perm2
        assert perm1 != perm3


class TestRoleEntity:
    def test_create_with_valid_data(self):
        role = Role.create(name=RoleName('admin'), description='Administrator')
        assert role.name.to_raw() == 'admin'
        assert role.description == 'Administrator'
        assert isinstance(role.role_id, RoleID)
        assert role.permissions == ()

    def test_create_with_permissions(self):
        perm = Permission(name='edit_users')
        role = Role(role_id=RoleID(uuid4()), name=RoleName('moderator'), permissions=(perm,))
        assert role.permissions == (perm,)
        assert role.has_permission('edit_users') is True

    def test_has_permission_returns_true_when_found(self):
        perm = Permission(name='delete_posts')
        role = Role(role_id=RoleID(uuid4()), name=RoleName('moderator'), permissions=(perm,))
        assert role.has_permission('delete_posts') is True

    def test_has_permission_returns_false_when_not_found(self):
        role = Role(role_id=RoleID(uuid4()), name=RoleName('moderator'))
        assert role.has_permission('nonexistent') is False

    def test_has_permission_empty_permissions(self):
        role = Role(role_id=RoleID(uuid4()), name=RoleName('user'))
        assert role.has_permission('anything') is False

    def test_add_permission_returns_new_role(self):
        perm = Permission(name='edit_posts')
        role = Role(role_id=RoleID(uuid4()), name=RoleName('moderator'))
        new_role = role.add_permission(perm)
        assert new_role is not role
        assert new_role.has_permission('edit_posts') is True
        assert role.has_permission('edit_posts') is False

    def test_add_permission_immutability(self):
        perm = Permission(name='edit_posts')
        role = Role(role_id=RoleID(uuid4()), name=RoleName('moderator'))
        _ = role.add_permission(perm)
        assert role.permissions == ()

    def test_add_existing_permission_returns_same_instance(self):
        perm = Permission(name='edit_posts')
        role = Role(role_id=RoleID(uuid4()), name=RoleName('moderator'), permissions=(perm,))
        new_role = role.add_permission(perm)
        assert new_role is role

    def test_remove_permission_returns_new_role(self):
        perm = Permission(name='edit_posts')
        role = Role(role_id=RoleID(uuid4()), name=RoleName('moderator'), permissions=(perm,))
        new_role = role.remove_permission('edit_posts')
        assert new_role is not role
        assert new_role.has_permission('edit_posts') is False
        assert role.has_permission('edit_posts') is True

    def test_remove_permission_immutability(self):
        perm = Permission(name='edit_posts')
        role = Role(role_id=RoleID(uuid4()), name=RoleName('moderator'), permissions=(perm,))
        _ = role.remove_permission('edit_posts')
        assert role.has_permission('edit_posts') is True

    def test_remove_nonexistent_permission_returns_new_role(self):
        role = Role(role_id=RoleID(uuid4()), name=RoleName('moderator'))
        new_role = role.remove_permission('nonexistent')
        assert new_role is not role
        assert new_role.permissions == ()

    def test_get_permissions(self):
        perm1 = Permission(name='edit_posts')
        perm2 = Permission(name='delete_posts')
        role = Role(role_id=RoleID(uuid4()), name=RoleName('moderator'), permissions=(perm1, perm2))
        assert role.permissions == (perm1, perm2)

    def test_create_records_role_created_event(self):
        role = Role.create(name=RoleName('editor'))
        events = role.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, RoleCreatedEvent)
        assert event.role_id == role.role_id.to_raw()
        assert event.name == 'editor'

    def test_create_records_single_event(self):
        role = Role.create(name=RoleName('viewer'))
        events = role.pull_events()
        assert len(events) == 1
        assert role.has_events() is False

    def test_remove_permission_records_role_updated_event(self):
        perm = Permission(name='edit')
        role = Role(role_id=RoleID(uuid4()), name=RoleName('editor'), permissions=(perm,))
        new_role = role.remove_permission('edit')
        events = new_role.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], RoleUpdatedEvent)
        assert events[0].updated_fields == ('permissions',)

    def test_remove_nonexistent_permission_records_no_event(self):
        role = Role(role_id=RoleID(uuid4()), name=RoleName('editor'))
        new_role = role.remove_permission('nonexistent')
        assert new_role.has_events() is False

    def test_immutability_frozen(self):
        role = Role(role_id=RoleID(uuid4()), name=RoleName('test'))
        with pytest.raises(AttributeError):
            role.name = 'changed'

    def test_pull_events_clears_events(self):
        role = Role.create(name=RoleName('tester'))
        assert len(role.pull_events()) == 1
        assert role.has_events() is False


class TestUserRoleEntity:
    def test_create_with_valid_data(self):
        user_id = uuid4()
        role_id = uuid4()
        ur = UserRole(user_id=UserID(user_id), role_id=RoleID(role_id))
        assert ur.user_id == UserID(user_id)
        assert ur.role_id == RoleID(role_id)
        assert ur.assigned_by is None
        assert isinstance(ur.assigned_at, datetime)

    def test_create_with_assigned_by(self):
        user_id = uuid4()
        role_id = uuid4()
        admin_id = uuid4()
        ur = UserRole(user_id=UserID(user_id), role_id=RoleID(role_id), assigned_by=UserID(admin_id))
        assert ur.assigned_by == UserID(admin_id)

    def test_assigned_at_defaults_to_utc_now(self):
        before = datetime.now(UTC)
        ur = UserRole(user_id=UserID(uuid4()), role_id=RoleID(uuid4()))
        after = datetime.now(UTC)
        assert before <= ur.assigned_at <= after

    def test_immutability(self):
        ur = UserRole(user_id=UserID(uuid4()), role_id=RoleID(uuid4()))
        with pytest.raises(AttributeError):
            ur.user_id = uuid4()


class TestRBACService:
    @pytest.fixture
    def mock_user_repo(self):
        repo = AsyncMock()
        repo.acquire_by_id = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_role_repo(self):
        repo = AsyncMock()
        repo.acquire_by_id = AsyncMock(return_value=None)
        repo.acquire_by_name = AsyncMock(return_value=None)
        repo.get_all = AsyncMock(return_value=[])
        repo.add = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        return repo

    @pytest.fixture
    def mock_permission_repo(self):
        repo = AsyncMock()
        repo.acquire_by_name = AsyncMock(return_value=None)
        repo.get_all = AsyncMock(return_value=[])
        repo.add = AsyncMock()
        return repo

    @pytest.fixture
    def mock_user_role_repo(self):
        repo = AsyncMock()
        repo.acquire_by_user_id = AsyncMock(return_value=[])
        repo.acquire_by_user_and_role = AsyncMock(return_value=None)
        repo.add = AsyncMock()
        repo.delete = AsyncMock()
        repo.delete_by_user_id = AsyncMock()
        return repo

    @pytest.fixture
    def service(self, mock_user_repo, mock_role_repo, mock_permission_repo, mock_user_role_repo):
        from application.user.rbac_service import RBACService
        return RBACService(
            user_repo=mock_user_repo,
            role_repo=mock_role_repo,
            permission_repo=mock_permission_repo,
            user_role_repo=mock_user_role_repo,
        )

    @pytest.mark.asyncio
    async def test_create_role_success(self, service, mock_role_repo):
        mock_role_repo.acquire_by_name = AsyncMock(return_value=None)

        role = await service.create_role(name=RoleName('editor'), description='Can edit content')

        assert role.name.to_raw() == 'editor'
        assert role.description == 'Can edit content'
        assert isinstance(role.role_id, RoleID)
        events = role.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], RoleCreatedEvent)
        mock_role_repo.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_role_without_description(self, service, mock_role_repo):
        mock_role_repo.acquire_by_name = AsyncMock(return_value=None)

        role = await service.create_role(name=RoleName('viewer'))

        assert role.name.to_raw() == 'viewer'
        assert role.description is None

    @pytest.mark.asyncio
    async def test_create_role_already_exists(self, service, mock_role_repo):
        existing = Role(role_id=RoleID(uuid4()), name=RoleName('editor'))
        mock_role_repo.acquire_by_name = AsyncMock(return_value=existing)

        with pytest.raises(RoleAlreadyExistsError):
            await service.create_role(name=RoleName('editor'))

        mock_role_repo.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_role_success(self, service, mock_role_repo, mock_user_role_repo):
        role = Role(role_id=RoleID(uuid4()), name=RoleName('editor'))
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        result = await service.delete_role(role.role_id)

        assert result.role_id == role.role_id
        events = result.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], RoleDeletedEvent)
        assert events[0].role_id == role.role_id.to_raw()
        mock_role_repo.delete.assert_called_once_with(role.role_id)

    @pytest.mark.asyncio
    async def test_delete_role_not_found(self, service, mock_role_repo):
        mock_role_repo.acquire_by_id = AsyncMock(return_value=None)

        with pytest.raises(RoleNotFoundError):
            await service.delete_role(RoleID(uuid4()))

        mock_role_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_admin_role_raises_error(self, service, mock_role_repo):
        role = Role(role_id=RoleID(uuid4()), name=RoleName('admin'))
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        with pytest.raises(PermissionDeniedError, match='Cannot delete admin role'):
            await service.delete_role(role.role_id)

        mock_role_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_assign_role_success(self, service, mock_user_repo, mock_role_repo, mock_user_role_repo):
        user_id = uuid4()
        role_id = uuid4()
        assigned_by = uuid4()

        user = _make_user(user_id)
        role = Role(role_id=RoleID(role_id), name=RoleName('editor'))

        mock_user_repo.acquire_by_id = AsyncMock(return_value=user)
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        result = await service.assign_role(
            user_id=UserID(user_id),
            role_id=RoleID(role_id),
            assigned_by=UserID(assigned_by),
        )

        assert result.id == user.id
        mock_user_role_repo.add.assert_called_once()
        added_ur = mock_user_role_repo.add.call_args[0][0]
        assert isinstance(added_ur, UserRole)
        assert added_ur.user_id == UserID(user_id)
        assert added_ur.role_id == RoleID(role_id)
        assert added_ur.assigned_by == UserID(assigned_by)

        events = result.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, UserRoleAssignedEvent)
        assert event.user_id == user_id
        assert event.role_id == role_id
        assert event.assigned_by == assigned_by

    @pytest.mark.asyncio
    async def test_assign_role_user_not_found(self, service, mock_user_repo, mock_role_repo):
        mock_user_repo.acquire_by_id = AsyncMock(return_value=None)

        with pytest.raises(UserNotFoundError):
            await service.assign_role(user_id=UserID(uuid4()), role_id=RoleID(uuid4()))

        mock_role_repo.acquire_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_assign_role_role_not_found(self, service, mock_user_repo, mock_role_repo):
        user = MagicMock()
        mock_user_repo.acquire_by_id = AsyncMock(return_value=user)
        mock_role_repo.acquire_by_id = AsyncMock(return_value=None)

        with pytest.raises(RoleNotFoundError):
            await service.assign_role(user_id=UserID(uuid4()), role_id=RoleID(uuid4()))

    @pytest.mark.asyncio
    async def test_assign_role_already_assigned(self, service, mock_user_repo, mock_role_repo, mock_user_role_repo):
        user_id = uuid4()
        role_id = uuid4()

        user = MagicMock()
        existing_ur = UserRole(user_id=UserID(user_id), role_id=RoleID(role_id))
        role = Role(role_id=RoleID(role_id), name=RoleName('editor'))

        mock_user_repo.acquire_by_id = AsyncMock(return_value=user)
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)
        mock_user_role_repo.acquire_by_user_and_role = AsyncMock(return_value=existing_ur)

        result = await service.assign_role(user_id=UserID(user_id), role_id=RoleID(role_id))

        assert result is user
        mock_user_role_repo.add.assert_not_called()
        user._record_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_role_success(self, service, mock_user_repo, mock_role_repo, mock_user_role_repo):
        user_id = uuid4()
        role_id = uuid4()

        user = _make_user(user_id)
        role = Role(role_id=RoleID(role_id), name=RoleName('editor'))

        mock_user_repo.acquire_by_id = AsyncMock(return_value=user)
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        result = await service.revoke_role(user_id=UserID(user_id), role_id=RoleID(role_id))

        assert result.id == user.id
        mock_user_role_repo.delete.assert_called_once_with(UserID(user_id), RoleID(role_id))

        events = result.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, UserRoleRevokedEvent)
        assert event.user_id == user_id
        assert event.role_id == role_id

    @pytest.mark.asyncio
    async def test_revoke_role_user_not_found(self, service, mock_user_repo):
        mock_user_repo.acquire_by_id = AsyncMock(return_value=None)

        with pytest.raises(UserNotFoundError):
            await service.revoke_role(user_id=UserID(uuid4()), role_id=RoleID(uuid4()))

    @pytest.mark.asyncio
    async def test_revoke_role_role_not_found(self, service, mock_user_repo, mock_role_repo):
        mock_user_repo.acquire_by_id = AsyncMock(return_value=MagicMock())
        mock_role_repo.acquire_by_id = AsyncMock(return_value=None)

        with pytest.raises(RoleNotFoundError):
            await service.revoke_role(user_id=UserID(uuid4()), role_id=RoleID(uuid4()))

    @pytest.mark.asyncio
    async def test_revoke_admin_role_raises_error(self, service, mock_user_repo, mock_role_repo, mock_user_role_repo):
        user_id = uuid4()
        role_id = uuid4()

        user = MagicMock()
        role = Role(role_id=RoleID(role_id), name=RoleName('admin'))

        mock_user_repo.acquire_by_id = AsyncMock(return_value=user)
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        with pytest.raises(PermissionDeniedError, match='Cannot revoke admin role'):
            await service.revoke_role(user_id=UserID(user_id), role_id=RoleID(role_id))

        mock_user_role_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_user_roles(self, service, mock_user_role_repo, mock_role_repo):
        user_id = uuid4()
        role1_id = uuid4()
        role2_id = uuid4()

        ur1 = UserRole(user_id=UserID(user_id), role_id=RoleID(role1_id))
        ur2 = UserRole(user_id=UserID(user_id), role_id=RoleID(role2_id))
        mock_user_role_repo.acquire_by_user_id = AsyncMock(return_value=[ur1, ur2])

        role1 = Role(role_id=RoleID(role1_id), name=RoleName('editor'))
        role2 = Role(role_id=RoleID(role2_id), name=RoleName('viewer'))
        mock_role_repo.acquire_by_id = AsyncMock(side_effect=[role1, role2])

        roles = await service.get_user_roles(UserID(user_id))

        assert len(roles) == 2
        assert roles[0].role_id == RoleID(role1_id)
        assert roles[1].role_id == RoleID(role2_id)
        mock_role_repo.acquire_by_id.assert_has_calls([
            call(RoleID(role1_id)),
            call(RoleID(role2_id)),
        ])

    @pytest.mark.asyncio
    async def test_get_user_roles_empty(self, service, mock_user_role_repo, mock_role_repo):
        mock_user_role_repo.acquire_by_user_id = AsyncMock(return_value=[])
        roles = await service.get_user_roles(UserID(uuid4()))
        assert roles == []

    @pytest.mark.asyncio
    async def test_get_user_roles_skips_missing_roles(self, service, mock_user_role_repo, mock_role_repo):
        user_id = uuid4()
        role1_id = uuid4()

        ur = UserRole(user_id=UserID(user_id), role_id=RoleID(role1_id))
        mock_user_role_repo.acquire_by_user_id = AsyncMock(return_value=[ur])
        mock_role_repo.acquire_by_id = AsyncMock(return_value=None)

        roles = await service.get_user_roles(UserID(user_id))
        assert roles == []

    @pytest.mark.asyncio
    async def test_has_permission_returns_true(self, service, mock_user_role_repo, mock_role_repo):
        user_id = uuid4()
        role_id = uuid4()
        perm = Permission(name='edit_posts')

        ur = UserRole(user_id=UserID(user_id), role_id=RoleID(role_id))
        mock_user_role_repo.acquire_by_user_id = AsyncMock(return_value=[ur])

        role = Role(role_id=RoleID(role_id), name=RoleName('editor'), permissions=(perm,))
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        result = await service.has_permission(UserID(user_id), 'edit_posts')
        assert result is True

    @pytest.mark.asyncio
    async def test_has_permission_returns_false(self, service, mock_user_role_repo, mock_role_repo):
        user_id = uuid4()
        role_id = uuid4()

        ur = UserRole(user_id=UserID(user_id), role_id=RoleID(role_id))
        mock_user_role_repo.acquire_by_user_id = AsyncMock(return_value=[ur])

        role = Role(role_id=RoleID(role_id), name=RoleName('editor'))
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        result = await service.has_permission(UserID(user_id), 'edit_posts')
        assert result is False

    @pytest.mark.asyncio
    async def test_has_permission_no_roles(self, service, mock_user_role_repo):
        mock_user_role_repo.acquire_by_user_id = AsyncMock(return_value=[])

        result = await service.has_permission(UserID(uuid4()), 'anything')
        assert result is False

    @pytest.mark.asyncio
    async def test_require_permission_passes(self, service, mock_user_role_repo, mock_role_repo):
        user_id = uuid4()
        role_id = uuid4()
        perm = Permission(name='edit_posts')

        ur = UserRole(user_id=UserID(user_id), role_id=RoleID(role_id))
        mock_user_role_repo.acquire_by_user_id = AsyncMock(return_value=[ur])

        role = Role(role_id=RoleID(role_id), name=RoleName('editor'), permissions=(perm,))
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        await service.require_permission(UserID(user_id), 'edit_posts')

    @pytest.mark.asyncio
    async def test_require_permission_raises_error(self, service, mock_user_role_repo, mock_role_repo):
        user_id = uuid4()
        role_id = uuid4()

        ur = UserRole(user_id=UserID(user_id), role_id=RoleID(role_id))
        mock_user_role_repo.acquire_by_user_id = AsyncMock(return_value=[ur])

        role = Role(role_id=RoleID(role_id), name=RoleName('editor'))
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        with pytest.raises(PermissionDeniedError):
            await service.require_permission(UserID(user_id), 'edit_posts')

    @pytest.mark.asyncio
    async def test_add_permission_to_role_success(self, service, mock_role_repo, mock_permission_repo):
        role_id = uuid4()
        permission_name = 'edit_posts'

        role = Role(role_id=RoleID(uuid4()), name=RoleName('editor'))
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        result = await service.add_permission_to_role(RoleID(role_id), permission_name)

        assert result.has_permission(permission_name) is True
        mock_role_repo.update.assert_called_once()
        events = result.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], RoleUpdatedEvent)
        assert events[0].role_id == result.role_id.to_raw()
        assert events[0].updated_fields == ('permissions',)

    @pytest.mark.asyncio
    async def test_add_permission_to_role_creates_new_permission(self, service, mock_role_repo, mock_permission_repo):
        role_id = uuid4()
        permission_name = 'new_perm'

        role = Role(role_id=RoleID(uuid4()), name=RoleName('editor'))
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)
        mock_permission_repo.acquire_by_name = AsyncMock(return_value=None)

        result = await service.add_permission_to_role(RoleID(role_id), permission_name)

        assert result.has_permission(permission_name) is True
        mock_permission_repo.add.assert_called_once()
        added_perm = mock_permission_repo.add.call_args[0][0]
        assert added_perm.name == permission_name

    @pytest.mark.asyncio
    async def test_add_permission_to_role_uses_existing_permission(self, service, mock_role_repo, mock_permission_repo):
        role_id = uuid4()
        permission_name = 'existing_perm'

        existing_perm = Permission(name=permission_name)
        role = Role(role_id=RoleID(uuid4()), name=RoleName('editor'))
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)
        mock_permission_repo.acquire_by_name = AsyncMock(return_value=existing_perm)

        result = await service.add_permission_to_role(RoleID(role_id), permission_name)

        assert result.has_permission(permission_name) is True
        mock_permission_repo.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_permission_to_role_role_not_found(self, service, mock_role_repo):
        mock_role_repo.acquire_by_id = AsyncMock(return_value=None)

        with pytest.raises(RoleNotFoundError):
            await service.add_permission_to_role(RoleID(uuid4()), 'perm')

        mock_role_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_permission_from_role_success(self, service, mock_role_repo):
        role_id = uuid4()
        perm = Permission(name='edit_posts')
        role = Role(role_id=RoleID(uuid4()), name=RoleName('editor'), permissions=(perm,))
        mock_role_repo.acquire_by_id = AsyncMock(return_value=role)

        result = await service.remove_permission_from_role(RoleID(role_id), 'edit_posts')

        assert result.has_permission('edit_posts') is False
        mock_role_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_permission_from_role_not_found(self, service, mock_role_repo):
        mock_role_repo.acquire_by_id = AsyncMock(return_value=None)

        with pytest.raises(RoleNotFoundError):
            await service.remove_permission_from_role(RoleID(uuid4()), 'perm')

        mock_role_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_all_roles(self, service, mock_role_repo):
        role1 = Role(role_id=RoleID(uuid4()), name=RoleName('admin'))
        role2 = Role(role_id=RoleID(uuid4()), name=RoleName('editor'))
        mock_role_repo.get_all = AsyncMock(return_value=[role1, role2])

        roles = await service.get_all_roles()

        assert len(roles) == 2
        assert roles[0].role_id == role1.role_id
        assert roles[1].role_id == role2.role_id

    @pytest.mark.asyncio
    async def test_get_all_roles_empty(self, service, mock_role_repo):
        mock_role_repo.get_all = AsyncMock(return_value=[])
        roles = await service.get_all_roles()
        assert roles == []

    @pytest.mark.asyncio
    async def test_get_all_permissions(self, service, mock_permission_repo):
        perm1 = Permission(name='edit_posts')
        perm2 = Permission(name='delete_posts')
        mock_permission_repo.get_all = AsyncMock(return_value=[perm1, perm2])

        permissions = await service.get_all_permissions()

        assert len(permissions) == 2
        assert permissions[0] == perm1
        assert permissions[1] == perm2

    @pytest.mark.asyncio
    async def test_get_all_permissions_empty(self, service, mock_permission_repo):
        mock_permission_repo.get_all = AsyncMock(return_value=[])
        permissions = await service.get_all_permissions()
        assert permissions == []


class TestCreateRoleUseCase:
    @pytest.fixture
    def mock_rbac_service(self):
        return MagicMock()

    @pytest.fixture
    def mock_uow(self):
        uow = MagicMock()
        uow.add_events = MagicMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.mark.asyncio
    async def test_create_role_success(self, mock_rbac_service, mock_uow):
        from application.user.commands.rbac import CreateRoleInput, CreateRoleUseCase

        role = Role.create(name=RoleName('editor'), description='Can edit')
        mock_rbac_service.create_role = AsyncMock(return_value=role)

        use_case = CreateRoleUseCase(rbac_service=mock_rbac_service, uow=mock_uow)
        result = await use_case(CreateRoleInput(name='editor', description='Can edit'))

        assert result.name == 'editor'
        assert result.description == 'Can edit'
        assert result.role_id == role.role_id.to_raw()
        mock_rbac_service.create_role.assert_called_once_with(RoleName('editor'), 'Can edit')
        mock_uow.add_events.assert_called_once()
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_role_without_description(self, mock_rbac_service, mock_uow):
        from application.user.commands.rbac import CreateRoleInput, CreateRoleUseCase

        role = Role.create(name=RoleName('viewer'))
        mock_rbac_service.create_role = AsyncMock(return_value=role)

        use_case = CreateRoleUseCase(rbac_service=mock_rbac_service, uow=mock_uow)
        result = await use_case(CreateRoleInput(name='viewer'))

        assert result.name == 'viewer'
        assert result.description is None
        mock_rbac_service.create_role.assert_called_once_with(RoleName('viewer'), None)

    @pytest.mark.asyncio
    async def test_create_role_already_exists(self, mock_rbac_service, mock_uow):
        from application.user.commands.rbac import CreateRoleInput, CreateRoleUseCase

        mock_rbac_service.create_role = AsyncMock(
            side_effect=RoleAlreadyExistsError('editor'),
        )

        use_case = CreateRoleUseCase(rbac_service=mock_rbac_service, uow=mock_uow)

        with pytest.raises(RoleAlreadyExistsError):
            await use_case(CreateRoleInput(name='editor'))

        mock_uow.add_events.assert_not_called()
        mock_uow.commit.assert_not_called()


class TestAssignRoleUseCase:
    @pytest.fixture
    def mock_rbac_service(self):
        return MagicMock()

    @pytest.fixture
    def mock_uow(self):
        uow = MagicMock()
        uow.add_events = MagicMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.mark.asyncio
    async def test_assign_role_success(self, mock_rbac_service, mock_uow):
        from application.user.commands.rbac import AssignRoleInput, AssignRoleUseCase

        user = MagicMock()
        user.pull_events = MagicMock(return_value=[])
        mock_rbac_service.assign_role = AsyncMock(return_value=user)

        use_case = AssignRoleUseCase(rbac_service=mock_rbac_service, uow=mock_uow)
        user_id = uuid4()
        role_id = uuid4()
        assigned_by = uuid4()

        await use_case(AssignRoleInput(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by,
        ))

        mock_rbac_service.assign_role.assert_called_once_with(
            user_id=UserID(user_id),
            role_id=RoleID(role_id),
            assigned_by=UserID(assigned_by),
        )
        user.pull_events.assert_called_once()
        mock_uow.add_events.assert_called_once_with([])
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_role_user_not_found(self, mock_rbac_service, mock_uow):
        from application.user.commands.rbac import AssignRoleInput, AssignRoleUseCase

        mock_rbac_service.assign_role = AsyncMock(
            side_effect=RoleNotFoundError(str(uuid4())),
        )

        use_case = AssignRoleUseCase(rbac_service=mock_rbac_service, uow=mock_uow)

        with pytest.raises(RoleNotFoundError):
            await use_case(AssignRoleInput(user_id=uuid4(), role_id=uuid4()))

        mock_uow.commit.assert_not_called()


class TestRevokeRoleUseCase:
    @pytest.fixture
    def mock_rbac_service(self):
        return MagicMock()

    @pytest.fixture
    def mock_uow(self):
        uow = MagicMock()
        uow.add_events = MagicMock()
        uow.commit = AsyncMock()
        return uow

    @pytest.mark.asyncio
    async def test_revoke_role_success(self, mock_rbac_service, mock_uow):
        from application.user.commands.rbac import RevokeRoleInput, RevokeRoleUseCase

        user = MagicMock()
        user.pull_events = MagicMock(return_value=[])
        mock_rbac_service.revoke_role = AsyncMock(return_value=user)

        use_case = RevokeRoleUseCase(rbac_service=mock_rbac_service, uow=mock_uow)
        user_id = uuid4()
        role_id = uuid4()

        await use_case(RevokeRoleInput(user_id=user_id, role_id=role_id))

        mock_rbac_service.revoke_role.assert_called_once_with(
            user_id=UserID(user_id),
            role_id=RoleID(role_id),
        )
        user.pull_events.assert_called_once()
        mock_uow.add_events.assert_called_once_with([])
        mock_uow.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_role_not_found(self, mock_rbac_service, mock_uow):
        from application.user.commands.rbac import RevokeRoleInput, RevokeRoleUseCase

        mock_rbac_service.revoke_role = AsyncMock(
            side_effect=RoleNotFoundError(str(uuid4())),
        )

        use_case = RevokeRoleUseCase(rbac_service=mock_rbac_service, uow=mock_uow)

        with pytest.raises(RoleNotFoundError):
            await use_case(RevokeRoleInput(user_id=uuid4(), role_id=uuid4()))

        mock_uow.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_revoke_admin_role_raises_error(self, mock_rbac_service, mock_uow):
        from application.user.commands.rbac import RevokeRoleInput, RevokeRoleUseCase

        mock_rbac_service.revoke_role = AsyncMock(
            side_effect=PermissionDeniedError('Cannot revoke admin role from user'),
        )

        use_case = RevokeRoleUseCase(rbac_service=mock_rbac_service, uow=mock_uow)

        with pytest.raises(PermissionDeniedError):
            await use_case(RevokeRoleInput(user_id=uuid4(), role_id=uuid4()))

        mock_uow.commit.assert_not_called()


class TestGetUserRolesUseCase:
    @pytest.fixture
    def mock_role_reader(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_user_roles_success(self, mock_role_reader):
        from application.user.queries.rbac import GetUserRolesUseCase
        from domain.user.interfaces.persistence.readers import RoleReadDTO

        dto1 = RoleReadDTO(role_id=uuid4(), name='editor', description='Can edit', permissions=())
        dto2 = RoleReadDTO(role_id=uuid4(), name='viewer', permissions=())

        mock_role_reader.get_user_roles = AsyncMock(return_value=[dto1, dto2])

        use_case = GetUserRolesUseCase(role_reader=mock_role_reader)
        user_id = uuid4()
        result = await use_case(user_id)

        assert len(result) == 2
        assert result[0] == dto1
        assert result[1] == dto2
        mock_role_reader.get_user_roles.assert_called_once_with(UserID(user_id))

    @pytest.mark.asyncio
    async def test_get_user_roles_empty(self, mock_role_reader):
        from application.user.queries.rbac import GetUserRolesUseCase

        mock_role_reader.get_user_roles = AsyncMock(return_value=[])

        use_case = GetUserRolesUseCase(role_reader=mock_role_reader)
        result = await use_case(uuid4())

        assert result == []


class TestCheckPermissionUseCase:
    @pytest.fixture
    def mock_role_reader(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_check_permission_returns_true(self, mock_role_reader):
        from application.user.queries.rbac import CheckPermissionUseCase
        from domain.user.interfaces.persistence.readers import RoleReadDTO

        dto = RoleReadDTO(role_id=uuid4(), name='editor', permissions=('edit_posts',))
        mock_role_reader.get_user_roles = AsyncMock(return_value=[dto])

        use_case = CheckPermissionUseCase(role_reader=mock_role_reader)
        result = await use_case(user_id=uuid4(), permission='edit_posts')

        assert result is True

    @pytest.mark.asyncio
    async def test_check_permission_returns_false(self, mock_role_reader):
        from application.user.queries.rbac import CheckPermissionUseCase
        from domain.user.interfaces.persistence.readers import RoleReadDTO

        dto = RoleReadDTO(role_id=uuid4(), name='editor', permissions=('view_posts',))
        mock_role_reader.get_user_roles = AsyncMock(return_value=[dto])

        use_case = CheckPermissionUseCase(role_reader=mock_role_reader)
        result = await use_case(user_id=uuid4(), permission='edit_posts')

        assert result is False


class TestGetAllRolesUseCase:
    @pytest.fixture
    def mock_role_reader(self):
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_all_roles_success(self, mock_role_reader):
        from application.user.queries.rbac import GetAllRolesUseCase
        from domain.user.interfaces.persistence.readers import RoleReadDTO

        dto1 = RoleReadDTO(role_id=uuid4(), name='admin', description='Admin', permissions=())
        dto2 = RoleReadDTO(role_id=uuid4(), name='editor', permissions=())
        mock_role_reader.get_all_roles = AsyncMock(return_value=[dto1, dto2])

        use_case = GetAllRolesUseCase(role_reader=mock_role_reader)
        result = await use_case()

        assert len(result) == 2
        assert result[0] == dto1
        assert result[1] == dto2

    @pytest.mark.asyncio
    async def test_get_all_roles_empty(self, mock_role_reader):
        from application.user.queries.rbac import GetAllRolesUseCase

        mock_role_reader.get_all_roles = AsyncMock(return_value=[])

        use_case = GetAllRolesUseCase(role_reader=mock_role_reader)
        result = await use_case()

        assert result == []
