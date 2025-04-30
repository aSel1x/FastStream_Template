from typing import AsyncIterable

from application.common.interfaces import UnitOfWorkInterface
from application.user.iteractors import CreateUserInteractor, ReadUserInteractor
from dishka import Provider, Scope, from_context, provide
from domain.user.interfaces import CryptInterface, UserRepositoryInterface
from domain.user.service import UserService
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from infrastructure.crypt import Crypt

# from infrastructure.db.memory.repositories import InMemoryUserRepo
# from infrastructure.db.memory.uow import InMemoryUoW
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.db.sqlalchemy.main import build_sa_engine, build_sa_session_factory
from infrastructure.db.sqlalchemy.repositories import SQLAlchemyUserRepo
from infrastructure.db.sqlalchemy.uow import SQLAlchemyUoW


class DiProvider(Provider):
    sqlalchemy_config = from_context(
        SQLAlchemyConfig,
        scope=Scope.APP,
    )

    @provide(scope=Scope.APP)
    async def get_crypt(self) -> CryptInterface:
        return Crypt()

    @provide(scope=Scope.APP)
    async def get_session_factory(
        self, sqlalchemy_config: SQLAlchemyConfig
    ) -> async_sessionmaker[AsyncSession]:
        async with build_sa_engine(sqlalchemy_config) as engine:
            return build_sa_session_factory(engine)

    @provide(scope=Scope.REQUEST)
    async def get_session(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> AsyncIterable[AsyncSession]:
        async with session_factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    async def get_uow(self, session: AsyncSession) -> UnitOfWorkInterface:
        return SQLAlchemyUoW(session=session)

    @provide(scope=Scope.REQUEST)
    async def get_user_repo(self, session: AsyncSession) -> UserRepositoryInterface:
        return SQLAlchemyUserRepo(session=session)

    @provide(scope=Scope.REQUEST)
    async def get_user_service(
        self, crypt: CryptInterface, user_repo: UserRepositoryInterface
    ) -> UserService:
        return UserService(crypt=crypt, user_repo=user_repo)

    create_user_interactor = provide(CreateUserInteractor, scope=Scope.REQUEST)
    read_user_interactor = provide(ReadUserInteractor, scope=Scope.REQUEST)
