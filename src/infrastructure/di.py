from collections.abc import AsyncGenerator
from uuid import uuid4

from application.common.interfaces import UnitOfWorkInterface, UUIDGeneratorInterface
from application.common.interfaces.event_bus import EventPublisherInterface
from application.user.interactors.create_user import CreateUserInteractor
from application.user.interactors.delete_me import DeleteMeInteractor
from application.user.interactors.get_me import GetMeInteractor
from application.user.interactors.login import LoginInteractor
from application.user.interactors.refresh_token import RefreshTokenInteractor
from application.user.interactors.update_profile import UpdateProfileInteractor
from domain.user.interfaces import CryptInterface, JWTInterface, UserRepositoryInterface
from domain.user.service import UserService
from spritze import Container, Scope, provider
from spritze.core.provider import Provider
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from infrastructure.crypt import Crypt
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.db.sqlalchemy.main import build_sa_session_factory
from infrastructure.db.sqlalchemy.repositories.user import SQLAlchemyUserRepo
from infrastructure.db.sqlalchemy.uow import SQLAlchemyUoW
from infrastructure.jwt import JWTService
from infrastructure.queue import EventPublisherAMQP, RabbitMQConfig


class AppContainer(Container):
    @provider(scope=Scope.APP)
    def event_publisher(
        self,
        rabbitmq_config: RabbitMQConfig,
    ) -> EventPublisherInterface:
        return EventPublisherAMQP(rabbitmq_config)

    crypt: Provider = provider(Crypt, provide_as=CryptInterface, scope=Scope.APP)
    jwt_service: Provider = provider(
        JWTService,
        provide_as=JWTInterface,
        scope=Scope.APP,
    )

    @provider(scope=Scope.APP)
    def uuid_generator(self) -> UUIDGeneratorInterface:
        return uuid4

    @provider(scope=Scope.APP)
    def db_engine(self, sqlalchemy_config: SQLAlchemyConfig) -> AsyncEngine:
        return create_async_engine(
            sqlalchemy_config.full_url,
            echo=sqlalchemy_config.echo,
            echo_pool=sqlalchemy_config.echo,
            pool_size=50,
        )

    session_factory: Provider = provider(build_sa_session_factory, scope=Scope.APP)

    @provider(scope=Scope.REQUEST)
    async def db_session(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    user_repo: Provider = provider(
        SQLAlchemyUserRepo,
        provide_as=UserRepositoryInterface,
        scope=Scope.REQUEST,
    )

    uow: Provider = provider(
        SQLAlchemyUoW,
        provide_as=UnitOfWorkInterface,
        scope=Scope.REQUEST,
    )

    user_service: Provider = provider(UserService, scope=Scope.REQUEST)

    create_user_interactor: Provider = provider(
        CreateUserInteractor, scope=Scope.REQUEST
    )
    login_interactor: Provider = provider(LoginInteractor, scope=Scope.REQUEST)
    refresh_token_interactor: Provider = provider(
        RefreshTokenInteractor, scope=Scope.REQUEST
    )
    get_me_interactor: Provider = provider(GetMeInteractor, scope=Scope.REQUEST)
    update_profile_interactor: Provider = provider(
        UpdateProfileInteractor, scope=Scope.REQUEST
    )
    delete_me_interactor: Provider = provider(DeleteMeInteractor, scope=Scope.REQUEST)
