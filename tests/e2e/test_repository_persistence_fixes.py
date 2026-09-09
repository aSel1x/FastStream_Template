"""Regression tests for SQLAlchemy repository methods that silently dropped state.

Covers:
- SQLAlchemyRoleRepo.update(): previously wrote only `description`, dropping both a role
  rename and any permission grant/revoke (add_permission_to_role/remove_permission_from_role
  called `update()` but nothing changed in role_permissions).
- SQLAlchemySessionRepo.add(): previously never inserted refresh_tokens rows, so every
  freshly-issued refresh token was unusable (acquire_by_token_hash could never find it).
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import Delete, Insert, Update


def _table_name(statement: Insert | Delete | Update) -> str:
    """The table a DML statement targets. `.table` is a FromClause, which may be a Join."""
    table = statement.table
    return table.name if isinstance(table, Table) else ''


class TestRoleRepoUpdate:
    @pytest.mark.asyncio
    async def test_update_persists_new_name_and_syncs_permissions(self) -> None:
        from domain.user.entities.rbac import Permission, Role
        from domain.user.value_objects import RoleID, RoleName
        from infrastructure.db.sqlalchemy.repositories.rbac import SQLAlchemyRoleRepo

        kept_id, removed_id, added_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        role = Role(
            role_id=RoleID(uuid.uuid4()),
            name=RoleName('renamed_role'),
            description='updated description',
            permissions=(Permission(name='kept_perm'), Permission(name='added_perm')),
        )

        session = AsyncMock(spec=AsyncSession)
        session.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: [kept_id, removed_id]))
        session.scalar = AsyncMock(side_effect=[kept_id, added_id])

        await SQLAlchemyRoleRepo(session).update(role)

        statements = [call.args[0] for call in session.execute.await_args_list]

        update_stmt = next(s for s in statements if isinstance(s, Update))
        assert _table_name(update_stmt) == 'roles'
        params = update_stmt.compile().params
        assert params['name'] == 'renamed_role'
        assert params['description'] == 'updated description'

        role_perm_inserts = [
            s for s in statements if isinstance(s, Insert) and _table_name(s) == 'role_permissions'
        ]
        assert len(role_perm_inserts) == 1
        assert role_perm_inserts[0].compile().params['permission_id'] == added_id

        role_perm_deletes = [
            s for s in statements if isinstance(s, Delete) and _table_name(s) == 'role_permissions'
        ]
        assert len(role_perm_deletes) == 1

        session.flush.assert_awaited_once()


class TestSessionRepoAdd:
    @pytest.mark.asyncio
    async def test_add_persists_refresh_tokens(self) -> None:
        from domain.user.entities.session import DeviceInfo, RefreshToken, SessionAggregate
        from domain.user.value_objects import TokenHash, UserID
        from infrastructure.db.sqlalchemy.repositories.session import SQLAlchemySessionRepo

        token = RefreshToken(token_hash=TokenHash(b'x' * 32))
        session_agg = SessionAggregate.create(UserID(uuid.uuid4()), DeviceInfo()).add_refresh_token(
            token
        )

        db_session = AsyncMock(spec=AsyncSession)

        await SQLAlchemySessionRepo(db_session).add(session_agg)

        statements = [call.args[0] for call in db_session.execute.await_args_list]
        insert_tables = [s.table.name for s in statements if isinstance(s, Insert)]
        assert insert_tables == ['sessions', 'refresh_tokens']

        refresh_insert = statements[insert_tables.index('refresh_tokens')]
        params = refresh_insert.compile().params
        assert params['id'] == token.id
        assert params['token_hash'] == token.token_hash.to_raw()

        db_session.flush.assert_awaited_once()
