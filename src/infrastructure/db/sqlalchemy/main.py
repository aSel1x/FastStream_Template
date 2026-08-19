from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def build_sa_session_factory(
    db_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
