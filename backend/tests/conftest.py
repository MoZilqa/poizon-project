import os

# до импорта приложения: отдельная БД в памяти, без бота
os.environ.update(DATABASE_URL="sqlite+aiosqlite:///:memory:", BOT_TOKEN="", ADMIN_IDS="1",
                  ADMIN_PASSWORD="secret", SECRET_KEY="test")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import db  # noqa: E402

# одна общая in-memory база на все соединения
db.engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=StaticPool)
db.Session.configure(bind=db.engine)

from app import models  # noqa: E402,F401
from app.api.main import app  # noqa: E402
from app.core.service import create_order, get_user  # noqa: E402


@pytest.fixture(autouse=True)
async def schema():
    async with db.engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)


@pytest.fixture
async def session():
    async with db.Session() as s:
        yield s


@pytest.fixture
async def order(session):
    u = await get_user(session, 42, "client", "Иван")
    return await create_order(session, u, {
        "url": "https://dw4.co/t/A/abc", "shot": "file-1", "size": "42", "cat": "shoes",
        "price": "500", "total": "8687.50", "fio": "Иванов Иван", "phone": "+79001234567", "pvz": "СДЭК, Ленина 1",
    })


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


@pytest.fixture
async def admin(client):
    token = (await client.post("/api/auth/login", json={"password": "secret"})).json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client
