import asyncio
from typing import Any

import pytest
from httpx import AsyncClient

from app import models

pytestmark = pytest.mark.asyncio(loop_scope='session')


async def test_user_create(http_client: AsyncClient, cache: dict[str, Any]) -> None:
    user_create = models.UserCreate(
        username='username',
        password='password',
    )
    r = await http_client.post(
        '/user/',
        json=user_create.model_dump()
    )

    assert r.status_code == 201

    cache.update(user_create=user_create)


async def test_user_auth(http_client: AsyncClient, cache: dict[str, Any]) -> None:
    await asyncio.sleep(0.2)
    user_create: models.UserCreate | None = cache.get('user_create')
    assert user_create is not None

    r = await http_client.post(
        '/user/oauth2',
        json=user_create.model_dump()
    )

    assert r.status_code == 200
    r_json = r.json()

    assert (user_auth := models.UserAuth(**r_json))

    cache.update(user_auth=user_auth)


async def test_user_retrieve(http_client: AsyncClient, cache: dict[str, Any]) -> None:
    user_create: models.UserCreate | None = cache.get('user_create')
    user_auth: models.UserAuth | None = cache.get('user_auth')
    assert user_create is not None
    assert user_auth is not None

    r = await http_client.get(
        '/user/',
        headers={'Authorization': f"Bearer {user_auth.access_token}"},
    )

    assert r.status_code == 200
    r_json = r.json()

    assert (user := models.UserBase(**r_json))

    assert user.username == user_create.username
    assert user.is_active is True
