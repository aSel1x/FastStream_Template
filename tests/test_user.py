from typing import Any

from app.models import User, UserAuth, UserCreate
from app.usecases import Services


async def test_user_create(
        service: Services,
        cache: dict[str, Any]
) -> None:
    user_create = UserCreate(
        username='username',
        password='password',
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
    user_create: UserCreate | None = cache.get('user_create')

    assert user_create is not None

    r: UserAuth = await service.user.auth(user_create.username, user_create.password)

    cache.update(user_auth=r)


async def test_user_retrieve(
        service: Services,
        cache: dict[str, Any]
) -> None:
    user: User | None = cache.get('user')
    user_auth: UserAuth | None = cache.get('user_auth')
    user_create: UserCreate | None = cache.get('user_create')

    assert user is not None
    assert user_auth is not None
    assert user_create is not None

    r: User | None = await service.user.retrieve_by_token(user_auth.token)

    assert r is not None

    assert r.id == user.id
    assert r.username == user_create.username
    assert service.security.pwd.checkpwd(user_create.password, r.password)
    assert r.is_active == user.is_active
