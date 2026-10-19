import os

# Must be set before the app modules import their settings and engine.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://studio:studio@localhost:54322/studio_test"
)
os.environ["SUPABASE_JWT_SECRET"] = "test-secret-for-studio-api-at-least-32-bytes"
os.environ["SUPABASE_URL"] = ""
os.environ["DAILY_PROJECT_LIMIT"] = "3"
os.environ["ENV"] = "development"
# Never let tests reach real model providers, whatever is in .env.
for _k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
    os.environ[_k] = ""
os.environ["LLM_CHAIN"] = '["groq"]'

import time  # noqa: E402
import uuid  # noqa: E402

import jwt  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.migrate import migrate  # noqa: E402


def make_token(user_id: uuid.UUID | None = None, *, expired: bool = False, secret: str | None = None) -> str:
    now = int(time.time())
    claims = {
        "sub": str(user_id or uuid.uuid4()),
        "email": "owner@example.com",
        "aud": "authenticated",
        "iat": now,
        "exp": now - 10 if expired else now + 3600,
    }
    return jwt.encode(claims, secret or os.environ["SUPABASE_JWT_SECRET"], algorithm="HS256")


@pytest.fixture(scope="session", autouse=True)
async def schema():
    await migrate(engine)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_tables():
    async with engine.begin() as conn:
        names = ", ".join(t.name for t in Base.metadata.sorted_tables)
        await conn.execute(text(f"truncate {names} restart identity cascade"))
    yield


@pytest.fixture
async def session():
    async with SessionLocal() as s:
        yield s


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def auth(user_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user_id)}"}
