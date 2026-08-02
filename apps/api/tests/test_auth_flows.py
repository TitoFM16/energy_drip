"""End-to-end auth flow tests against a real database.

Unlike test_availability.py (pure logic, mocked repositories), these
exercise the full stack — HTTP -> router -> service -> Postgres — because
the value here is in the interactions: token hashing round-trips, refresh
rotation actually invalidating the old token, invite/reset expiry checks
against real timestamps. Requires a reachable DATABASE_URL; skipped otherwise.

The app's `engine` (medical_api.core.database) is a module-level singleton
whose pooled asyncpg connections bind to whichever event loop first used
them. pytest-asyncio's default is a fresh loop per test function, so a
connection checked back into the pool by one test and handed to the next
raises "Event loop is closed". Pinning this whole module to one shared
session-scoped loop (and a matching session-scoped client) avoids that
entirely — it's what the engine's actual lifetime already assumes.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from medical_api.core.config import get_settings
from medical_api.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(scope="session")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _db_reachable() -> bool:
    probe_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        async with probe_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await probe_engine.dispose()


@pytest.fixture(autouse=True, scope="session")
async def _skip_without_db():
    if not await _db_reachable():
        pytest.skip("no reachable database for auth integration tests")


async def _register_org(client) -> dict:
    response = await client.post(
        "/api/v1/auth/register-organization",
        json={
            "organization_name": f"Test Clinic {uuid.uuid4()}",
            "admin_email": f"admin-{uuid.uuid4()}@example.com",
            "admin_password": "supersecret123",
            "admin_full_name": "Admin Person",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_register_organization_returns_working_tokens(client):
    body = await _register_org(client)
    assert body["organization_id"]
    assert body["access_token"]
    assert body["refresh_token"]

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["roles"] == ["organization_admin"]


async def test_refresh_rotates_token_and_invalidates_the_old_one(client):
    body = await _register_org(client)
    old_refresh = body["refresh_token"]

    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["refresh_token"]
    assert new_refresh != old_refresh

    reuse_attempt = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_attempt.status_code == 401

    still_works = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert still_works.status_code == 200


async def test_logout_revokes_refresh_token(client):
    body = await _register_org(client)
    refresh_token = body["refresh_token"]

    logout = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204

    reuse_attempt = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reuse_attempt.status_code == 401


async def test_invite_accept_creates_user_with_invited_role(client):
    org = await _register_org(client)
    admin_headers = {"Authorization": f"Bearer {org['access_token']}"}

    invite_email = f"staff-{uuid.uuid4()}@example.com"
    invite = await client.post(
        "/api/v1/auth/invites",
        json={"email": invite_email, "role": "receptionist"},
        headers=admin_headers,
    )
    assert invite.status_code == 201, invite.text
    invite_token = invite.json()["token"]

    accept = await client.post(
        f"/api/v1/auth/invites/{invite_token}/accept",
        json={"full_name": "New Staff", "password": "anothersecret123"},
    )
    assert accept.status_code == 201, accept.text

    me = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {accept.json()['access_token']}"}
    )
    assert me.json()["email"] == invite_email
    assert me.json()["roles"] == ["receptionist"]

    # Single-use: accepting again must fail.
    replay = await client.post(
        f"/api/v1/auth/invites/{invite_token}/accept",
        json={"full_name": "Replay", "password": "yetanothersecret"},
    )
    assert replay.status_code == 410


async def test_invite_requires_organization_admin_role(client):
    org = await _register_org(client)
    # Create a receptionist (no invite permission), then try to invite as them.
    invite = await client.post(
        "/api/v1/auth/invites",
        json={"email": f"staff-{uuid.uuid4()}@example.com", "role": "receptionist"},
        headers={"Authorization": f"Bearer {org['access_token']}"},
    )
    receptionist_accept = await client.post(
        f"/api/v1/auth/invites/{invite.json()['token']}/accept",
        json={"full_name": "Front Desk", "password": "receptionistpw123"},
    )
    receptionist_token = receptionist_accept.json()["access_token"]

    forbidden = await client.post(
        "/api/v1/auth/invites",
        json={"email": f"other-{uuid.uuid4()}@example.com", "role": "receptionist"},
        headers={"Authorization": f"Bearer {receptionist_token}"},
    )
    assert forbidden.status_code == 403


async def test_login_resolves_the_single_organization_without_an_org_id(client):
    # register-organization's response doesn't echo the admin email/password
    # back, so accept an invite to get a known email/password pair to log in
    # with.
    org = await _register_org(client)
    invite_email = f"login-check-{uuid.uuid4()}@example.com"
    invite = await client.post(
        "/api/v1/auth/invites",
        json={"email": invite_email, "role": "receptionist"},
        headers={"Authorization": f"Bearer {org['access_token']}"},
    )
    accept = await client.post(
        f"/api/v1/auth/invites/{invite.json()['token']}/accept",
        json={"full_name": "Login Check", "password": "checklogin123"},
    )
    assert accept.status_code == 201, accept.text

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": invite_email, "password": "checklogin123"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]

    wrong_password = await client.post(
        "/api/v1/auth/login",
        json={"email": invite_email, "password": "not-the-password"},
    )
    assert wrong_password.status_code == 401


async def test_password_reset_flow(client):
    reset_request = await client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "admin@nonexistent.example.com"},
    )
    # Same 200 shape whether or not the account exists — token is only
    # populated for a real account (see PasswordResetRequestResponse).
    assert reset_request.status_code == 200
    assert reset_request.json()["token"] is None

    confirm_bad_token = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": "not-a-real-token", "new_password": "brandnewpassword1"},
    )
    assert confirm_bad_token.status_code == 400
