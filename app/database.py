from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base


engine = None
SessionLocal = None


def init_database(database_url: str) -> None:
    global engine
    global SessionLocal

    engine = create_async_engine(
    database_url,
    echo=False,
    pool_pre_ping=True,
    connect_args={"ssl": None}
)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables() -> None:
    if engine is None:
        raise RuntimeError("Database is not initialized. Call init_database() first.")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if SessionLocal is None:
        raise RuntimeError("Session factory is not initialized. Call init_database() first.")
    async with SessionLocal() as session:
        yield session
