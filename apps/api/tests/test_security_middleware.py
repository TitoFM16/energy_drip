"""Coverage for the security-headers/trusted-host/body-size-limit slice of
"API and application security hardening" in missing_features.md. No
database needed — these are pure ASGI-layer checks.
"""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.middleware.trustedhost import TrustedHostMiddleware

from medical_api.core.middleware import SecurityHeadersMiddleware
from medical_api.main import app as real_app


async def test_responses_carry_baseline_security_headers():
    transport = ASGITransport(app=real_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    # Test settings run with environment=development — HSTS must never be
    # sent outside production (see SecurityHeadersMiddleware's docstring).
    assert "strict-transport-security" not in response.headers


async def test_hsts_header_is_sent_only_when_configured_for_production():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware, is_production=True)

    @app.get("/")
    async def root() -> dict[str, bool]:
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.headers["strict-transport-security"] == "max-age=63072000; includeSubDomains"


async def test_oversized_request_body_is_rejected_before_reaching_a_route():
    transport = ASGITransport(app=real_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            content=b"irrelevant",
            headers={"content-length": "99999999999"},
        )
    assert response.status_code == 413


async def test_trusted_host_middleware_rejects_an_unrecognized_host():
    app = FastAPI()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["example.com"])

    @app.get("/")
    async def root() -> dict[str, bool]:
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://not-allowed.test") as client:
        response = await client.get("/")
    assert response.status_code == 400
