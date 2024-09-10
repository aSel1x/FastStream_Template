from typing import Any

from app.models import UserCreate, User, UserAuth
from app.usecases import Services


async def test_user_create(
        service: Services,
        cache: dict[str, Any]
) -> None:
    user_create = UserCreate(
        username="username",
        password="password",
    )
    cache.update(user_create=user_create)

    r: User = await service.user.create(user_create)

    assert r.username == user_create.username
    assert service.security.pwd.checkpwd(user_create.password, r.password)

    cache.update(user=r)


async def test_user_auth(
        service: Services,
        cache: dict[str, Any]
) -> None:
    user_create: UserCreate = cache.get("user_create")

    r: UserAuth = await service.user.auth(user_create.username, user_create.password)

    cache.update(user_auth=r)


async def test_user_retrieve(
        service: Services,
        cache: dict[str, Any]
) -> None:
    user: User = cache.get("user")
    user_auth: UserAuth = cache.get("user_auth")
    user_create: UserCreate = cache.get("user_create")

    r: User = await service.user.retrieve_by_token(user_auth.token)

    assert r is not None

    assert r.id == user.id
    assert r.username == user_create.username
    assert service.security.pwd.checkpwd(user_create.password, r.password)
    assert r.is_active == user.is_active
