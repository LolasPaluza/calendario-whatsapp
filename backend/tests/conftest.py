import os
# Set env vars before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "123")
os.environ.setdefault("WHATSAPP_ACCESS_TOKEN", "test")
os.environ.setdefault("WEBHOOK_VERIFY_TOKEN", "test_key")
os.environ.setdefault("API_KEY", "test_key")
os.environ.setdefault("WHATSAPP_USER_PHONE", "5511999999999")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database import Base
import models  # noqa: F401 — registers models with Base

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def app_client(db):
    from main import app
    from database import get_db
    from httpx import AsyncClient, ASGITransport
    from unittest.mock import patch, AsyncMock
    app.dependency_overrides[get_db] = lambda: db
    with patch("main.load_pending_reminders", new_callable=AsyncMock), \
         patch("main.scheduler"):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": "test_key"},
        ) as client:
            yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def app_client_no_auth(db):
    from main import app
    from database import get_db
    from httpx import AsyncClient, ASGITransport
    from unittest.mock import patch, AsyncMock
    app.dependency_overrides[get_db] = lambda: db
    with patch("main.load_pending_reminders", new_callable=AsyncMock), \
         patch("main.scheduler"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client
    app.dependency_overrides.clear()
