from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from medical_api.api.error_handlers import register_error_handlers
from medical_api.api.router import api_router
from medical_api.core.config import get_settings
from medical_api.core.logging import configure_logging
from medical_api.integrations.object_storage.client import ensure_bucket_exists

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    if not settings.is_production:
        # Dev/test convenience: the local MinIO bucket doesn't exist until
        # something creates it, and nothing in the Docker stack did — the
        # first consent submission would 500 on signature upload with
        # NoSuchBucket. See ensure_bucket_exists() for why this is gated to
        # non-production.
        ensure_bucket_exists()
    yield


app = FastAPI(title="Medical Platform API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
