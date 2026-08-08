"""Coverage for the "Rate limiting for login... consent links" bullet under
"API and application security hardening" in missing_features.md: brute-force
protection on /auth/login, and token-guessing protection on invite-accept
and password-reset.

Deliberately does NOT hit the real endpoints enough times to trip the real
Redis counter (unlike a normal integration test) — httpx's ASGITransport
gives every test in the suite the same fake client IP (127.0.0.1, see
core/middleware.py), and Redis isn't reset between tests the way the
database is (no savepoint-rollback equivalent). Actually exhausting a
shared `login:127.0.0.1` counter here would risk 5-15 minutes of spurious
429s in every other test in this file (and test_auth_flows.py) that also
calls these endpoints. test_booking.py's existing rate-limit test avoids
the same trap by calling `check_rate_limit` directly with a random key
instead of the real endpoint; this module takes the equivalent approach for
an endpoint-level test by monkeypatching `check_rate_limit` itself to
return False, which proves the router is actually wired to it (and that a
denial really does surface as 429) without touching real Redis state.
"""

import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from medical_api.core.config import get_settings
from medical_api.core.database import engine, get_db
from medical_api.main import app
from medical_api.modules.identity import router as identity_router

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    connection = await engine.connect()
    outer_transaction = await connection.begin()
    session = AsyncSession(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )

    async def override_get_db():
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as async_client:
            yield async_client
    finally:
        del app.dependency_overrides[get_db]
        await session.close()
        await outer_transaction.rollback()
        await connection.close()


async def _db_reachable() -> bool:
    probe_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with probe_engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await probe_engine.dispose()


@pytest.fixture(autouse=True, scope="session")
async def _skip_without_db():
    if not await _db_reachable():
        pytest.skip("no reachable database for auth-rate-limiting tests")


def _deny_rate_limit(monkeypatch) -> None:
    monkeypatch.setattr(identity_router, "check_rate_limit", AsyncMock(return_value=False))


async def test_login_is_rate_limited(client, monkeypatch):
    _deny_rate_limit(monkeypatch)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": f"nobody-{uuid.uuid4()}@example.com", "password": "whatever123"},
    )
    assert response.status_code == 429


async def test_invite_accept_is_rate_limited(client, monkeypatch):
    _deny_rate_limit(monkeypatch)
    response = await client.post(
        "/api/v1/auth/invites/not-a-real-token/accept",
        json={"full_name": "Someone", "password": "whatever123"},
    )
    assert response.status_code == 429


async def test_password_reset_request_is_rate_limited(client, monkeypatch):
    _deny_rate_limit(monkeypatch)
    response = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": f"nobody-{uuid.uuid4()}@example.com"},
    )
    assert response.status_code == 429


async def test_password_reset_confirm_is_rate_limited(client, monkeypatch):
    _deny_rate_limit(monkeypatch)
    response = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": "whatever123"},
    )
    assert response.status_code == 429
