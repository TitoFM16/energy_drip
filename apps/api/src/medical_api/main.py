from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from medical_api.api.error_handlers import register_error_handlers
from medical_api.api.router import api_router
from medical_api.core.config import get_settings
from medical_api.core.database import engine
from medical_api.core.logging import configure_logging
from medical_api.core.middleware import (
    BodySizeLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from medical_api.core.schema_check import assert_schema_matches_head
from medical_api.integrations.object_storage.client import ensure_bucket_exists

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    # Runs in every environment, not just production: a worker or a
    # differently-started API instance running old code against a newer
    # schema (or vice versa) is exactly as possible in local dev as in
    # production, and failing loudly at startup beats a confusing runtime
    # error from the first request that touches the mismatched table/column.
    await assert_schema_matches_head(engine)
    ensure_bucket_exists()
    settings.public_media_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Medical Platform API", version="0.1.0", lifespan=lifespan)

# Middleware added earliest ends up outermost (Starlette wraps in reverse
# registration order) — the two raw rejection checks go first so an
# oversized body or a spoofed Host header is refused before CORS, routing,
# or anything else does any work.
app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
if settings.is_production:
    # Only enforced in production — see allowed_hosts' comment in
    # core/config.py for why a wrong/missing value here must never risk
    # breaking local dev, CI, or the E2E stack.
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Populates request_id/ip/user_agent for AuditService; added after
# CORSMiddleware so CORS stays outermost (of these two) and still handles
# preflight OPTIONS.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SecurityHeadersMiddleware, is_production=settings.is_production)

register_error_handlers(app)
app.include_router(api_router)
app.mount(
    "/media", StaticFiles(directory=settings.public_media_path, check_dir=False), name="media"
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Pure liveness — the process is up and able to handle a request.
    Deliberately checks nothing else: an orchestrator using this to decide
    whether to kill/restart the process shouldn't restart a perfectly
    healthy API just because a downstream dependency is briefly down (that
    would compound an outage, not fix it). See /health/ready for the
    dependency-aware check.
    """
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness_check(response: Response) -> dict[str, str]:
    """Dependency-aware readiness — for load balancer / orchestrator
    routing decisions ("should traffic go to this instance right now"),
    not for triggering restarts. Checks Postgres, the only shared runtime dependency.
    """
    checks = {}
    try:
        async with engine.connect() as connection:
            await connection.exec_driver_sql("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    if any(v != "ok" for v in checks.values()):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return checks
