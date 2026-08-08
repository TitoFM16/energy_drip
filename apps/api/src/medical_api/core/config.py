from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://medical:medical@localhost:5432/medical_platform"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    # Used only for signing presigned download URLs handed to a browser —
    # server-to-server calls (upload_bytes/download_bytes) always use
    # s3_endpoint_url. In docker-compose, s3_endpoint_url is the internal
    # Docker-network hostname (http://minio:9000), which a browser outside
    # the network can't resolve; s3_public_endpoint_url is the
    # host-reachable address (http://localhost:9000) a browser can
    # actually use. Falls back to s3_endpoint_url when unset, which is
    # correct for non-Docker setups (both point at the same reachable
    # host, e.g. `make dev`'s .env.example).
    s3_public_endpoint_url: str | None = None
    s3_access_key: str = "medical"
    s3_secret_key: str = "medical123"
    s3_bucket: str = "medical-platform"

    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    invite_expire_days: int = 7
    password_reset_expire_hours: int = 2
    algorithm: str = "HS256"

    # WhatsApp is the only outbound notification channel this product uses —
    # see the "Product scope correction" / notification-automation notes in
    # docs/missing_features.md. No SMS provider is integrated.
    whatsapp_api_token: str = ""
    whatsapp_phone_number_id: str = ""
    # Meta App Secret — used to verify the X-Hub-Signature-256 header on
    # incoming delivery-status webhook callbacks (never sent to Meta).
    whatsapp_app_secret: str = ""
    # Arbitrary shared string configured in Meta's App Dashboard when
    # registering the webhook URL; Meta echoes it back on the GET
    # challenge-response handshake so we can confirm the request is really
    # from a webhook registration attempt we authorized.
    whatsapp_webhook_verify_token: str = ""

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174"]
    # Only enforced when environment=production (see main.py) — a wrong or
    # missing value here would otherwise risk breaking every non-production
    # environment (local dev, CI's docker-compose stack, the E2E suite),
    # which all reach the API through different hostnames.
    allowed_hosts: list[str] = []
    max_request_body_bytes: int = 10_000_000

    # Base URL of the patient-web app, used to build the consent link sent
    # over WhatsApp (`{patient_web_base_url}/c/{token}` — see
    # apps/patient-web's router). Matches the dev-mode link staff-web shows
    # in its own "Solicitar consentimiento" UI.
    patient_web_base_url: str = "http://localhost:5174"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
