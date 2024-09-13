from typing import Any

import pytest

from app import models
from app.usecases import Services

pytestmark = pytest.mark.asyncio(loop_scope='session')


async def test_user_create(
        use_cases: Services,
        cache: dict[str, Any]
) -> None:
    user_create = models.UserCreate(
        username='username',
        password='password',
    )
    cache.update(user_create=user_create)

    o_user: models.User = await use_cases.user.create(user_create)

    assert o_user.username == user_create.username
    assert use_cases.security.pwd.checkpwd(user_create.password, o_user.password)

    cache.update(user=o_user)


async def test_user_auth(
        use_cases: Services,
        cache: dict[str, Any]
) -> None:
    user_create: models.UserCreate | None = cache.get('user_create')
    i_user: models.User | None = cache.get('user')
    assert user_create is not None
    assert i_user is not None

    user_auth: models.UserAuth = await use_cases.user.oauth2(i_user)

    cache.update(user_auth=user_auth)


async def test_user_retrieve(
        use_cases: Services,
        cache: dict[str, Any]
) -> None:
    user_create: models.UserCreate | None = cache.get('user_create')
    user_auth: models.UserAuth | None = cache.get('user_auth')
    i_user: models.User | None = cache.get('user')
    assert user_create is not None
    assert user_auth is not None
    assert i_user is not None

    o_user: models.User = await use_cases.user.retrieve_by_token(user_auth.access_token)

    assert o_user.id == i_user.id
    assert o_user.username == o_user.username
    assert use_cases.security.pwd.checkpwd(user_create.password, o_user.password)
    assert o_user.is_active == i_user.is_active
