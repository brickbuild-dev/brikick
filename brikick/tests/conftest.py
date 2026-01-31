import asyncio
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, INET, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlalchemy import BigInteger

import db.models  # noqa: F401
from api.deps import get_current_user, get_db
from api.main import app
from db.base import Base
from db.models.users import User


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(type_, compiler, **kw) -> str:
    return "TEXT"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw) -> str:
    return "JSON"


@compiles(INET, "sqlite")
def _compile_inet_sqlite(type_, compiler, **kw) -> str:
    return "TEXT"


@compiles(BYTEA, "sqlite")
def _compile_bytea_sqlite(type_, compiler, **kw) -> str:
    return "BLOB"


@compiles(BigInteger, "sqlite")
def _compile_bigint_sqlite(type_, compiler, **kw) -> str:
    return "INTEGER"


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

async_session_test = async_sessionmaker(
    engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_test() as session:
        yield session
        await session.rollback()

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    from tests.factories.user_factory import UserFactory

    user = await UserFactory.create(db_session)
    return user


@pytest.fixture
async def test_seller(db_session: AsyncSession) -> User:
    from tests.factories.store_factory import StoreFactory
    from tests.factories.user_factory import UserFactory

    user = await UserFactory.create(db_session, roles=["seller"])
    store = await StoreFactory.create(db_session, user_id=user.id)
    user.store = store
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    from tests.factories.user_factory import UserFactory

    return await UserFactory.create(db_session, roles=["admin"])
