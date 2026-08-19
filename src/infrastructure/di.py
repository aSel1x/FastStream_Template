from collections.abc import AsyncGenerator
from uuid import uuid4

import httpx
import redis.asyncio as redis

from application.common.interfaces import EventHandler, UnitOfWorkInterface, UUIDGeneratorInterface
from application.common.interfaces.system.cache import CacheInterface
from application.common.interfaces.acl.hydra_admin import HydraAdminClientInterface
from application.common.interfaces.system.rate_limiter import (
    LoginAttemptLimiterInterface,
    RateLimiterInterface,
)
from application.hydra_clients.commands.create_client import CreateOAuthClientUseCase
from application.hydra_clients.commands.delete_client import DeleteOAuthClientUseCase
from application.hydra_clients.commands.rotate_client_secret import RotateClientSecretUseCase
from application.hydra_clients.queries.list_clients import ListOAuthClientsUseCase
from application.user.commands.change_password import ChangePasswordUseCase
from application.user.commands.create_user import CreateUserUseCase
from application.user.commands.delete_me import DeleteMeUseCase
from application.user.commands.login import LoginUseCase
from application.user.commands.manage_2fa import (
    Enable2FAUseCase,
    Disable2FAUseCase,
    Verify2FAUseCase,
)
from application.user.commands.manage_sessions import RevokeAllSessionsUseCase, RevokeSessionUseCase
from application.user.commands.rbac import (
    AddPermissionToRoleUseCase,
    AssignRoleUseCase,
    CreateRoleUseCase,
    DeleteRoleUseCase,
    RemovePermissionFromRoleUseCase,
    RevokeRoleUseCase,
)
from application.user.commands.refresh_token import RefreshTokenUseCase
from application.user.commands.reset_password import (
    RequestPasswordResetUseCase,
    ResetPasswordUseCase,
)
from application.user.commands.update_profile import UpdateProfileUseCase
from application.user.commands.verify_email import VerifyEmailUseCase
from application.user.queries.get_me import GetMeUseCase
from application.user.queries.manage_sessions import GetUserSessionsUseCase
from application.user.queries.rbac import (
    CheckPermissionUseCase,
    GetAllRolesUseCase,
    GetUserRolesUseCase,
    ListPermissionsUseCase,
)
from domain.user.interfaces.persistence.readers import RoleReader, SessionReader, UserReader
from infrastructure.db.sqlalchemy.repositories.readers import (
    SQLAlchemyRoleReader,
    SQLAlchemySessionReader,
    SQLAlchemyUserReader,
)
from application.user.services import UserService
from application.user.rbac_service import RBACService
from domain.audit import AuditEventHandler, AuditRepositoryInterface
from domain.user.interfaces import (
    CryptInterface,
    SessionRepositoryInterface,
    TwoFactorInterface,
    UserRepositoryInterface,
)
from domain.user.interfaces.persistence.rbac import (
    PermissionRepositoryInterface,
    RoleRepositoryInterface,
    UserRoleRepositoryInterface,
)
from dishka import Provider, Scope
from dishka import provide  # pyright: ignore[reportUnknownVariableType]
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from infrastructure.cache.config import CacheConfig
from infrastructure.cache.memory_cache import InMemoryCache
from infrastructure.cache.redis_cache import RedisCache
from infrastructure.crypt import Crypt
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.db.sqlalchemy.main import build_sa_session_factory
from infrastructure.db.sqlalchemy.repositories.audit import SQLAlchemyAuditLogRepo
from infrastructure.db.sqlalchemy.repositories.rbac import (
    SQLAlchemyPermissionRepo,
    SQLAlchemyRoleRepo,
    SQLAlchemyUserRoleRepo,
)
from infrastructure.db.sqlalchemy.repositories.session import SQLAlchemySessionRepo
from infrastructure.db.sqlalchemy.repositories.user import SQLAlchemyUserRepo
from infrastructure.db.sqlalchemy.uow import SQLAlchemyUoW
from infrastructure.email import EmailSenderInterface, SMTPSender
from infrastructure.hydra import HydraAdminClient, HydraConfig
from infrastructure.idempotency import IdempotencyStore
from infrastructure.security.rate_limiter import (
    InMemoryLoginAttemptLimiter,
    InMemoryRateLimiter,
    RateLimitConfig,
)
from infrastructure.security.redis_rate_limiter import RedisLoginAttemptLimiter, RedisRateLimiter
from infrastructure.two_factor import TwoFactorAuth


class AppProvider(Provider):
    def __init__(self) -> None:
        super().__init__()

        _ = self.provide(Crypt, provides=CryptInterface, scope=Scope.APP)
        _ = self.provide(TwoFactorAuth, provides=TwoFactorInterface, scope=Scope.APP)
        _ = self.provide(IdempotencyStore, scope=Scope.APP)
        _ = self.provide(SMTPSender, provides=EmailSenderInterface, scope=Scope.APP)
        _ = self.provide(build_sa_session_factory, scope=Scope.APP)

        _ = self.provide(SQLAlchemyUserRepo, provides=UserRepositoryInterface, scope=Scope.REQUEST)
        _ = self.provide(
            SQLAlchemySessionRepo, provides=SessionRepositoryInterface, scope=Scope.REQUEST
        )
        _ = self.provide(
            SQLAlchemyPermissionRepo, provides=PermissionRepositoryInterface, scope=Scope.REQUEST
        )
        _ = self.provide(SQLAlchemyRoleRepo, provides=RoleRepositoryInterface, scope=Scope.REQUEST)
        _ = self.provide(
            SQLAlchemyUserRoleRepo, provides=UserRoleRepositoryInterface, scope=Scope.REQUEST
        )
        _ = self.provide(
            SQLAlchemyAuditLogRepo, provides=AuditRepositoryInterface, scope=Scope.REQUEST
        )

        _ = self.provide(SQLAlchemyUserReader, provides=UserReader, scope=Scope.REQUEST)
        _ = self.provide(SQLAlchemySessionReader, provides=SessionReader, scope=Scope.REQUEST)
        _ = self.provide(SQLAlchemyRoleReader, provides=RoleReader, scope=Scope.REQUEST)

        _ = self.provide(UserService, scope=Scope.REQUEST)
        _ = self.provide(RBACService, scope=Scope.REQUEST)

        _ = self.provide(CreateOAuthClientUseCase, scope=Scope.REQUEST)
        _ = self.provide(ListOAuthClientsUseCase, scope=Scope.REQUEST)
        _ = self.provide(DeleteOAuthClientUseCase, scope=Scope.REQUEST)
        _ = self.provide(RotateClientSecretUseCase, scope=Scope.REQUEST)

        _ = self.provide(CreateUserUseCase, scope=Scope.REQUEST)
        _ = self.provide(LoginUseCase, scope=Scope.REQUEST)
        _ = self.provide(RefreshTokenUseCase, scope=Scope.REQUEST)
        _ = self.provide(GetMeUseCase, scope=Scope.REQUEST)
        _ = self.provide(UpdateProfileUseCase, scope=Scope.REQUEST)
        _ = self.provide(ChangePasswordUseCase, scope=Scope.REQUEST)
        _ = self.provide(DeleteMeUseCase, scope=Scope.REQUEST)

        _ = self.provide(Enable2FAUseCase, scope=Scope.REQUEST)
        _ = self.provide(Disable2FAUseCase, scope=Scope.REQUEST)
        _ = self.provide(Verify2FAUseCase, scope=Scope.REQUEST)

        _ = self.provide(VerifyEmailUseCase, scope=Scope.REQUEST)
        _ = self.provide(RequestPasswordResetUseCase, scope=Scope.REQUEST)
        _ = self.provide(ResetPasswordUseCase, scope=Scope.REQUEST)

        _ = self.provide(RevokeSessionUseCase, scope=Scope.REQUEST)
        _ = self.provide(RevokeAllSessionsUseCase, scope=Scope.REQUEST)
        _ = self.provide(GetUserSessionsUseCase, scope=Scope.REQUEST)

        _ = self.provide(AssignRoleUseCase, scope=Scope.REQUEST)
        _ = self.provide(RevokeRoleUseCase, scope=Scope.REQUEST)
        _ = self.provide(GetUserRolesUseCase, scope=Scope.REQUEST)
        _ = self.provide(CheckPermissionUseCase, scope=Scope.REQUEST)
        _ = self.provide(CreateRoleUseCase, scope=Scope.REQUEST)
        _ = self.provide(DeleteRoleUseCase, scope=Scope.REQUEST)
        _ = self.provide(GetAllRolesUseCase, scope=Scope.REQUEST)
        _ = self.provide(AddPermissionToRoleUseCase, scope=Scope.REQUEST)
        _ = self.provide(RemovePermissionFromRoleUseCase, scope=Scope.REQUEST)
        _ = self.provide(ListPermissionsUseCase, scope=Scope.REQUEST)

    @provide(scope=Scope.APP)
    def uuid_generator(self) -> UUIDGeneratorInterface:
        return uuid4

    @provide(scope=Scope.APP)
    async def redis_client(self, config: RateLimitConfig) -> AsyncGenerator[redis.Redis, None]:
        client = redis.Redis.from_url(config.redis_url)  # pyright: ignore[reportUnknownMemberType]
        yield client
        await client.aclose()

    @provide(scope=Scope.APP)
    def rate_limiter(
        self, config: RateLimitConfig, redis_client: redis.Redis
    ) -> RateLimiterInterface:
        if config.backend == "redis":
            return RedisRateLimiter(redis_client, config.max_requests, config.window_seconds)
        return InMemoryRateLimiter(config)

    @provide(scope=Scope.APP)
    def login_attempt_limiter(
        self,
        config: RateLimitConfig,
        redis_client: redis.Redis,
    ) -> LoginAttemptLimiterInterface:
        if config.backend == "redis":
            return RedisLoginAttemptLimiter(
                redis_client, config.max_login_attempts, config.lockout_seconds
            )
        return InMemoryLoginAttemptLimiter(config)

    @provide(scope=Scope.APP)
    def cache(self, config: CacheConfig, redis_client: redis.Redis) -> CacheInterface:
        if config.backend == "redis":
            return RedisCache(redis_client)
        return InMemoryCache()

    @provide(scope=Scope.APP)
    async def hydra_http_client(
        self, config: HydraConfig
    ) -> AsyncGenerator[httpx.AsyncClient, None]:
        client = httpx.AsyncClient(
            base_url=config.admin_url, timeout=config.request_timeout_seconds
        )
        yield client
        await client.aclose()

    @provide(scope=Scope.APP)
    def hydra_admin_client(
        self, http_client: httpx.AsyncClient, config: HydraConfig
    ) -> HydraAdminClient:
        return HydraAdminClient(http_client, config)

    @provide(scope=Scope.APP)
    def hydra_admin_client_interface(self, client: HydraAdminClient) -> HydraAdminClientInterface:
        return client

    @provide(scope=Scope.APP)
    def db_engine(self, sqlalchemy_config: SQLAlchemyConfig) -> AsyncEngine:
        return create_async_engine(
            sqlalchemy_config.full_url,
            echo=sqlalchemy_config.echo,
            echo_pool=sqlalchemy_config.echo,
            pool_size=50,
        )

    @provide(scope=Scope.REQUEST)
    async def db_session(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def uow(
        self,
        session: AsyncSession,
        audit_event_handler: AuditEventHandler,
    ) -> UnitOfWorkInterface:
        handlers: list[EventHandler] = [audit_event_handler.handle]
        return SQLAlchemyUoW(session, event_handlers=handlers)

    @provide(scope=Scope.REQUEST)
    def audit_event_handler(
        self,
        audit_repo: AuditRepositoryInterface,
    ) -> AuditEventHandler:
        return AuditEventHandler(audit_repo)
