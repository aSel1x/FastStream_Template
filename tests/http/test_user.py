import asyncio
from typing import Any

from httpx import AsyncClient

from app import models


async def test_user_create(http_client: AsyncClient, cache: dict[str, Any]) -> None:
    user_create = models.UserCreate(
        username="username",
        password="password",
    )
    r = await http_client.post(
        "/user/",
        json=user_create.model_dump()
    )

    assert r.status_code == 200
    cache.update(user_create=user_create)

async def test_user_auth(http_client: AsyncClient, cache: dict[str, Any]) -> None:
    await asyncio.sleep(0.2)
    user_create: models.UserCreate | None = cache.get("user_create")
    assert user_create is not None

    r = await http_client.post(
        "/user/auth",
        json=user_create.model_dump()
    )

    assert r.status_code == 200

    r_json = r.json()

    assert (user_token := r_json["token"]) is not None

    cache.update(user_token=user_token)

async def test_user_retrieve(http_client: AsyncClient, cache: dict[str, Any]) -> None:
    user_create: models.UserCreate | None = cache.get("user_create")
    user_token: str | None = cache.get("user_token")
    assert user_create is not None
    assert user_token is not None

    r = await http_client.get(
        "/user/",
        headers={"Authorization": f"Bearer {user_token}"},
    )

    assert r.status_code == 200

    r_json = r.json()

    assert r_json["username"] == user_create.username
    assert r_json["is_active"] is True
