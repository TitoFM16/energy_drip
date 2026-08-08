from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from medical_api.main import app
from medical_api.modules.booking import router as booking_router
from medical_api.modules.identity import router as identity_router


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
def _bypass_rate_limiting(monkeypatch):
    """Every test shares one fake client IP (httpx's ASGITransport always
    reports 127.0.0.1 — see core/middleware.py), and Redis rate-limit
    counters aren't reset between tests the way the database is (no
    savepoint-rollback equivalent). Without this, ordinary test setup that
    legitimately calls a rate-limited endpoint many times across the whole
    suite (e.g. accepting an invite once per test, in dozens of unrelated
    test files) trips the real limit and fails with a spurious 429 that has
    nothing to do with what the test is actually checking.

    Tests that specifically exercise rate limiting
    (test_auth_rate_limiting.py; test_booking.py's
    test_rate_limit_allows_up_to_the_limit_then_blocks, which calls
    check_rate_limit directly rather than through a router) set their own
    monkeypatch within the test body, which cleanly overrides this default
    for just that test.
    """
    monkeypatch.setattr(identity_router, "check_rate_limit", AsyncMock(return_value=True))
    monkeypatch.setattr(booking_router, "check_rate_limit", AsyncMock(return_value=True))
