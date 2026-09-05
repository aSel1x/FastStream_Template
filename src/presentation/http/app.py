import os
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from uuid import UUID

from dishka import AsyncContainer, make_async_container
from dishka.integrations.litestar import LitestarProvider, setup_dishka
from litestar import Litestar
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.contrib.opentelemetry import OpenTelemetryConfig, OpenTelemetryPlugin
from litestar.middleware import DefineMiddleware
from litestar.openapi.config import OpenAPIConfig
from litestar.plugins import PluginProtocol
from litestar.template.config import TemplateConfig

from application.user.commands.rbac import (
    AddPermissionToRoleInput,
    AddPermissionToRoleUseCase,
    AssignRoleInput,
    AssignRoleUseCase,
    CreateRoleInput,
    CreateRoleUseCase,
)
from application.user.queries.rbac import GetAllRolesUseCase
from application.user.rbac_service import RBACService
from domain.common.exceptions import BaseAppError, BaseDomainError
from infrastructure.cache.config import CacheConfig
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.di import AppProvider
from infrastructure.email import EmailConfig
from infrastructure.hydra import HydraAdminClient, HydraAdminError, HydraClientCreate, HydraConfig
from infrastructure.oauth.config import OAuthSeedConfig
from infrastructure.observability import setup_tracing
from infrastructure.observability.logging import configure_logging
from infrastructure.queue import RabbitMQConfig
from infrastructure.security.rate_limiter import RateLimitConfig
from infrastructure.settings import Settings
from presentation.http.controllers.admin import AdminClientsController
from presentation.http.controllers.health import HealthController
from presentation.http.controllers.hydra_bridge import HydraBridgeController
from presentation.http.controllers.roles import PermissionsController, RolesController
from presentation.http.controllers.user import (
    AuthController,
    SessionController,
    UserController,
)
from presentation.http.exception_handlers import (
    app_exception_handler,
    domain_exception_handler,
    hydra_admin_error_handler,
)
from presentation.http.guards import ADMIN_PERMISSION
from presentation.http.middleware.cors import AppCORSConfig
from presentation.http.middleware.https_redirect import HTTPSRedirectMiddleware
from presentation.http.middleware.request_id import RequestIDMiddleware
from presentation.http.middleware.security_headers import SecurityHeadersMiddleware
from presentation.http.security import create_hydra_auth


async def seed_oauth_clients(container: AsyncContainer) -> None:
    config = OAuthSeedConfig.from_environ()
    if not config.clients:
        return

    async with container() as request_container:
        hydra_client = await request_container.get(HydraAdminClient)

        for seed in config.clients:
            existing = await hydra_client.get_client(seed.client_id)
            if existing is not None:
                continue

            _ = await hydra_client.create_client(
                HydraClientCreate(
                    client_id=seed.client_id,
                    client_name=seed.client_name,
                    client_secret=seed.client_secret or None,
                    redirect_uris=list(seed.redirect_uris),
                    grant_types=list(seed.grant_types),
                    response_types=['code'] if 'authorization_code' in seed.grant_types else [],
                    scope=list(seed.scopes),
                    token_endpoint_auth_method='client_secret_basic'
                    if seed.is_confidential
                    else 'none',
                )
            )


async def seed_admin_role(container: AsyncContainer) -> None:
    async with container() as request_container:
        list_roles = await request_container.get(GetAllRolesUseCase)
        create_role = await request_container.get(CreateRoleUseCase)
        add_permission = await request_container.get(AddPermissionToRoleUseCase)

        role = next(
            (r for r in await list_roles() if r.name == RBACService.DEFAULT_ROLE_ADMIN),
            None,
        )
        if role is None:
            role = await create_role(
                CreateRoleInput(RBACService.DEFAULT_ROLE_ADMIN, 'Administrator')
            )
        if ADMIN_PERMISSION not in role.permissions:
            role = await add_permission(AddPermissionToRoleInput(role.role_id, ADMIN_PERMISSION))

        initial_admin_user_id = os.getenv('INITIAL_ADMIN_USER_ID')
        if initial_admin_user_id:
            assign_role = await request_container.get(AssignRoleUseCase)
            await assign_role(
                AssignRoleInput(
                    user_id=UUID(initial_admin_user_id),
                    role_id=role.role_id,
                )
            )


@asynccontextmanager
async def _lifespan(container: AsyncContainer) -> AsyncGenerator[None]:
    yield
    await container.close()


def get_litestar() -> Litestar:
    # Everything the environment is read for, validated here and only here. A misconfigured
    # service now fails at boot with the offending variable named, not at first use.
    settings = Settings.load()
    configure_logging()
    tracer_provider = setup_tracing(settings.observability)

    container = make_async_container(
        AppProvider(),
        LitestarProvider(),
        context={
            HydraConfig: settings.hydra,
            RabbitMQConfig: settings.rabbitmq,
            SQLAlchemyConfig: settings.database,
            EmailConfig: settings.email,
            RateLimitConfig: settings.rate_limit,
            CacheConfig: settings.cache,
        },
    )

    hydra_auth = create_hydra_auth()

    is_production = settings.is_production
    cors_config = AppCORSConfig.default()
    if is_production:
        allowed_origins = (
            os.getenv('ALLOWED_ORIGINS', '').split(',') if os.getenv('ALLOWED_ORIGINS') else None
        )
        cors_config = AppCORSConfig.production(allowed_origins)

    app_secret_key = settings.app_secret_key

    # Only the server-rendered Hydra login/consent forms need CSRF protection — the JSON API is
    # bearer-token authenticated and carries no ambient browser credentials for CSRF to exploit.
    csrf_config = CSRFConfig(
        secret=app_secret_key or secrets.token_urlsafe(32),
        exclude=['/v1', '/admin', '/health', '/schema', '/auth/logout'],
    )

    openapi_config = OpenAPIConfig(
        title='Backend Template API',
        version='1.0.0',
        description='User identity service backing Ory Hydra as login & consent provider',
    )

    template_dir = Path(__file__).resolve().parent / 'templates'

    plugins: list[PluginProtocol] = []
    if tracer_provider is not None:
        plugins.append(OpenTelemetryPlugin(OpenTelemetryConfig(tracer_provider=tracer_provider)))

    app = Litestar(
        route_handlers=[
            UserController,
            AuthController,
            SessionController,
            HealthController,
            HydraBridgeController,
            AdminClientsController,
            RolesController,
            PermissionsController,
        ],
        exception_handlers={
            BaseAppError: app_exception_handler,
            BaseDomainError: domain_exception_handler,
            HydraAdminError: hydra_admin_error_handler,
        },
        middleware=[
            DefineMiddleware(RequestIDMiddleware),
            DefineMiddleware(HTTPSRedirectMiddleware, enabled=is_production),
            DefineMiddleware(SecurityHeadersMiddleware, hsts=is_production),
        ],
        cors_config=cors_config,
        csrf_config=csrf_config,
        on_app_init=[hydra_auth.on_app_init],
        debug=not is_production,
        openapi_config=openapi_config,
        on_startup=[
            partial(seed_oauth_clients, container),
            partial(seed_admin_role, container),
        ],
        lifespan=[_lifespan(container)],
        plugins=plugins,
        template_config=TemplateConfig(
            directory=template_dir,
            engine=JinjaTemplateEngine,
        ),
    )

    setup_dishka(container=container, app=app)

    return app
