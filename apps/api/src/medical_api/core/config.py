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

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174"]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
