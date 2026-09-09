"""Every registered use case must actually be constructible.

A missing provider, a service that grew a constructor argument, or a port with no binding all
ship green today: no test resolves anything from the container, and the health endpoint touches
none of it. This walks the whole graph instead.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from dishka import Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.cache.config import CacheConfig
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.di import AppProvider
from infrastructure.email import EmailConfig
from infrastructure.hydra import HydraConfig
from infrastructure.queue import RabbitMQConfig
from infrastructure.security.rate_limiter import RateLimitConfig

USE_CASE_NAMES = [
    'CreateUserUseCase',
    'LoginUseCase',
    'RefreshTokenUseCase',
    'GetMeUseCase',
    'BuildConsentClaimsUseCase',
    'UpdateProfileUseCase',
    'ChangePasswordUseCase',
    'DeleteMeUseCase',
    'Enable2FAUseCase',
    'Confirm2FAUseCase',
    'CompleteTwoFactorUseCase',
    'Disable2FAUseCase',
    'Verify2FAUseCase',
    'VerifyEmailUseCase',
    'RequestPasswordResetUseCase',
    'ResetPasswordUseCase',
    'RevokeSessionUseCase',
    'RevokeAllSessionsUseCase',
    'GetUserSessionsUseCase',
    'AssignRoleUseCase',
    'RevokeRoleUseCase',
    'GetUserRolesUseCase',
    'CheckPermissionUseCase',
    'CreateRoleUseCase',
    'DeleteRoleUseCase',
    'GetAllRolesUseCase',
    'AddPermissionToRoleUseCase',
    'RemovePermissionFromRoleUseCase',
    'ListPermissionsUseCase',
    'CreateOAuthClientUseCase',
    'ListOAuthClientsUseCase',
    'DeleteOAuthClientUseCase',
    'RotateClientSecretUseCase',
]


class _FakeSessionProvider(AppProvider):
    """AppProvider with the database session replaced, so no server is needed."""

    @provide(scope=Scope.REQUEST, override=True)
    def db_session(self) -> AsyncSession:
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        return session


def _use_case_types() -> dict[str, type]:
    import infrastructure.di as di_module

    return {name: getattr(di_module, name) for name in USE_CASE_NAMES}


@pytest.fixture
def container():
    return make_async_container(
        _FakeSessionProvider(),
        context={
            HydraConfig: HydraConfig.from_environ(),
            RabbitMQConfig: RabbitMQConfig.from_environ(),
            SQLAlchemyConfig: SQLAlchemyConfig.from_environ(),
            EmailConfig: EmailConfig.from_environ(),
            RateLimitConfig: RateLimitConfig.from_environ(),
            CacheConfig: CacheConfig.from_environ(),
        },
    )


@pytest.mark.parametrize('name', USE_CASE_NAMES)
@pytest.mark.asyncio
async def test_use_case_is_resolvable(container, name: str) -> None:
    use_case_type = _use_case_types()[name]
    async with container() as request_container:
        resolved = await request_container.get(use_case_type)
        assert isinstance(resolved, use_case_type)
    await container.close()


@pytest.mark.asyncio
async def test_every_registered_use_case_is_covered() -> None:
    """The list above must not drift from what the container actually registers."""
    import infrastructure.di as di_module

    registered = {
        name
        for name in dir(di_module)
        if name.endswith('UseCase') and isinstance(getattr(di_module, name), type)
    }
    assert registered == set(USE_CASE_NAMES), (
        f'use cases missing from the DI graph test: {sorted(registered - set(USE_CASE_NAMES))}'
    )
