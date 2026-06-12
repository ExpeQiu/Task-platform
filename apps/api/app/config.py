import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://taskplatform:taskplatform@localhost:5432/taskplatform"
    database_url_sync: str = "postgresql://taskplatform:taskplatform@localhost:5432/taskplatform"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: str = "http://localhost:8000"
    webhook_secret: str = "dev-webhook-secret-change-me"
    webhook_hmac_enabled: bool = False
    log_level: str = "INFO"
    default_timeout_seconds: int = 300
    watchdog_interval_seconds: int = 60
    max_auto_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()


def setup_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
