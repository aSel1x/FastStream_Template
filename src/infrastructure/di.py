from collections.abc import AsyncGenerator

from application.common.interfaces import UnitOfWorkInterface
from application.user.iteractors.create import CreateUserInteractor
from application.user.iteractors.delete_me import DeleteMeInteractor
from application.user.iteractors.get_me import GetMeInteractor
from application.user.iteractors.login import LoginInteractor
from application.user.iteractors.refresh_token import RefreshTokenInteractor
from application.user.iteractors.update_profile import UpdateProfileInteractor
from domain.user.interfaces import CryptInterface, JWTInterface, UserRepositoryInterface
from domain.user.service import UserService
from spritze import Container, ContextField, Scope, context, provider
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
    jwt_config_ctx: ContextField[JWTConfig] = context.get(JWTConfig)
    rabbitmq_config_ctx: ContextField[RabbitMQConfig] = context.get(RabbitMQConfig)
    sqlalchemy_config_ctx: ContextField[SQLAlchemyConfig] = context.get(
        SQLAlchemyConfig
    )

    @provider(scope=Scope.APP)
    def event_bus(self) -> EventBus:
        return EventBus()

    @provider(scope=Scope.APP)
    def event_publisher(self, rabbitmq_config: RabbitMQConfig) -> EventPublisher:
        return EventPublisher(rabbitmq_config)

    @provider(scope=Scope.APP)
    def crypt(self) -> CryptInterface:
        return Crypt()

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

    @provider(scope=Scope.APP)
    def session_factory(self, db_engine: AsyncEngine) -> SessionFactory:
        return SessionFactory(db_engine)

    @provider(scope=Scope.REQUEST)
    async def db_session(
        self, session_factory: SessionFactory
    ) -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    @provider(scope=Scope.REQUEST)
    def user_repo(self, db_session: AsyncSession) -> UserRepositoryInterface:
        return SQLAlchemyUserRepo(db_session)

    @provider(scope=Scope.REQUEST)
    def uow(
        self,
        db_session: AsyncSession,
        event_bus: EventBus,
        event_publisher: EventPublisher,
    ) -> UnitOfWorkInterface:
        return SQLAlchemyUoW(
            session=db_session,
            event_bus=event_bus,
            event_publisher=event_publisher,
        )

    @provider(scope=Scope.REQUEST)
    def user_service(
        self,
        crypt: CryptInterface,
        user_repo: UserRepositoryInterface,
    ) -> UserService:
        return UserService(
            user_repo=user_repo,
            crypt=crypt,
        )

    @provider(scope=Scope.REQUEST)
    def create_user_interactor(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
    ) -> CreateUserInteractor:
        return CreateUserInteractor(uow=uow, user_service=user_service)

    @provider(scope=Scope.REQUEST)
    def login_interactor(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
        jwt_service: JWTInterface,
    ) -> LoginInteractor:
        return LoginInteractor(
            uow=uow,
            user_service=user_service,
            jwt_service=jwt_service,
        )

    @provider(scope=Scope.REQUEST)
    def refresh_token_interactor(
        self,
        jwt_service: JWTInterface,
    ) -> RefreshTokenInteractor:
        return RefreshTokenInteractor(jwt_service=jwt_service)

    @provider(scope=Scope.REQUEST)
    def get_me_interactor(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
    ) -> GetMeInteractor:
        return GetMeInteractor(uow=uow, user_service=user_service)

    @provider(scope=Scope.REQUEST)
    def update_profile_interactor(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
    ) -> UpdateProfileInteractor:
        return UpdateProfileInteractor(uow=uow, user_service=user_service)

    @provider(scope=Scope.REQUEST)
    def delete_me_interactor(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
    ) -> DeleteMeInteractor:
        return DeleteMeInteractor(uow=uow, user_service=user_service)
