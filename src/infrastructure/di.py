from collections.abc import AsyncGenerator

from application.common.interfaces import UnitOfWorkInterface
from application.user.iteractors.create_user import CreateUserInteractor
from application.user.iteractors.delete_me import DeleteMeInteractor
from application.user.iteractors.get_me import GetMeInteractor
from application.user.iteractors.login import LoginInteractor
from application.user.iteractors.refresh_token import RefreshTokenInteractor
from application.user.iteractors.update_profile import UpdateProfileInteractor
from domain.user.interfaces import CryptInterface, JWTInterface, UserRepositoryInterface
from domain.user.service import UserService
from spritze import Container, ContextField, Scope, provider
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

from infrastructure.crypt import Crypt
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.db.sqlalchemy.main import SessionFactory
from infrastructure.db.sqlalchemy.repositories.user import SQLAlchemyUserRepo
from infrastructure.db.sqlalchemy.uow import SQLAlchemyUoW
from infrastructure.jwt import JWTConfig, JWTService
from infrastructure.mediator import EventBus
from infrastructure.queue import EventPublisher, RabbitMQConfig


class AppContainer(Container):
    jwt_config_ctx: ContextField[JWTConfig] = ContextField(JWTConfig)
    rabbitmq_config_ctx: ContextField[RabbitMQConfig] = ContextField(RabbitMQConfig)
    sqlalchemy_config_ctx: ContextField[SQLAlchemyConfig] = ContextField(
        SQLAlchemyConfig
    )

    event_bus: object = provider(EventBus, scope=Scope.APP)
    event_publisher: object = provider(EventPublisher, scope=Scope.APP)

    crypt: object = provider(Crypt, provides=CryptInterface, scope=Scope.APP)

    @provider(scope=Scope.APP)
    def jwt_service(self, jwt_config: JWTConfig) -> JWTInterface:
        return JWTService(
            secret_key=jwt_config.secret_key,
            algorithm=jwt_config.algorithm,
        )

    @provider(scope=Scope.APP)
    def db_engine(self, sqlalchemy_config: SQLAlchemyConfig) -> AsyncEngine:
        return create_async_engine(
            sqlalchemy_config.full_url,
            echo=sqlalchemy_config.echo,
            echo_pool=sqlalchemy_config.echo,
            pool_size=50,
        )

    session_factory: object = provider(SessionFactory, scope=Scope.APP)

    @provider(scope=Scope.REQUEST)
    async def db_session(
        self, session_factory: SessionFactory
    ) -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    user_repo: object = provider(
        SQLAlchemyUserRepo,
        provides=UserRepositoryInterface,
        scope=Scope.REQUEST,
    )

    uow: object = provider(
        SQLAlchemyUoW,
        provides=UnitOfWorkInterface,
        scope=Scope.REQUEST,
    )

    user_service: object = provider(UserService, scope=Scope.REQUEST)

    create_user_interactor: object = provider(CreateUserInteractor, scope=Scope.REQUEST)
    login_interactor: object = provider(LoginInteractor, scope=Scope.REQUEST)
    refresh_token_interactor: object = provider(
        RefreshTokenInteractor, scope=Scope.REQUEST
    )
    get_me_interactor: object = provider(GetMeInteractor, scope=Scope.REQUEST)
    update_profile_interactor: object = provider(
        UpdateProfileInteractor, scope=Scope.REQUEST
    )
    delete_me_interactor: object = provider(DeleteMeInteractor, scope=Scope.REQUEST)
