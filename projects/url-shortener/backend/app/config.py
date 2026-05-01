from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://urlshortener:urlshortener@localhost:5432/urlshortener"
    ALEMBIC_DATABASE_URL: str | None = None

    TEMPORAL_HOST: str = "localhost:7233"
    TEMPORAL_NAMESPACE: str = "default"
    TEMPORAL_TASK_QUEUE: str = "urlshortener"

    PUBLIC_BASE_URL: str = "http://localhost:8080"
    SAFE_BROWSING_API_KEY: str | None = None
    RATE_LIMIT_SHORTEN: str = "10/minute"

    SLUG_LENGTH: int = 7
    MAX_SLUG_RETRIES: int = 5
    MAX_URL_LENGTH: int = 2048
    BLOCK_PRIVATE_IPS: bool = True
    ALLOWED_SCHEMES: tuple[str, ...] = ("http", "https")
    RESERVED_SLUGS: frozenset[str] = frozenset(
        {"api", "healthz", "readyz", "s", "admin", "www", "static"}
    )

    CLICK_FLUSH_INTERVAL_SECONDS: int = 60
    CLICK_FLUSH_THRESHOLD: int = 100
    CLICK_CONTINUE_AS_NEW_AT: int = 10_000

    SAFE_BROWSING_RECHECK_BATCH: int = 500
    SAFE_BROWSING_RECHECK_CONCURRENCY: int = 10

    ENV: str = Field(default="dev", description="dev | prod | test")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
