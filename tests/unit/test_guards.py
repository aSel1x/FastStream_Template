from unittest.mock import MagicMock

import pytest
from litestar.exceptions import PermissionDeniedException

from presentation.http.guards import require_scope
from presentation.http.security import UserSecuritySchema


class TestRequireScope:
    @pytest.mark.asyncio
    async def test_allows_when_scope_present(self):
        connection = MagicMock()
        connection.user = UserSecuritySchema(user_id=MagicMock(), scopes={'openid', 'profile'})

        guard = require_scope('profile')
        await guard(connection, MagicMock())

    @pytest.mark.asyncio
    async def test_denies_when_scope_missing(self):
        connection = MagicMock()
        connection.user = UserSecuritySchema(user_id=MagicMock(), scopes={'openid'})

        guard = require_scope('profile')
        with pytest.raises(PermissionDeniedException):
            await guard(connection, MagicMock())
