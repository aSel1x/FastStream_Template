from pydantic import PostgresDsn
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession


def new_session_maker(psql_dsn: PostgresDsn) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        psql_dsn.unicode_string(),
        pool_size=15,
        max_overflow=15,
    )
    return async_sessionmaker(engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)
