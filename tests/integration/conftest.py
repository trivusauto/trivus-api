import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.shared.infrastructure.settings import get_settings


@pytest_asyncio.fixture
async def session():  # type: ignore[misc]
    engine = create_async_engine(get_settings().database_url)
    conn = await engine.connect()
    trans = await conn.begin()
    maker = async_sessionmaker(bind=conn, expire_on_commit=False)
    s = maker()
    try:
        yield s
    finally:
        await s.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()
