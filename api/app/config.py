from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = "postgresql+asyncpg://studio:studio@localhost:54322/studio"

    # Supabase Auth. Projects with asymmetric signing keys verify through JWKS (supabase_url);
    # legacy projects and the test suite use the shared HS256 secret.
    supabase_url: str | None = None
    supabase_jwt_secret: str | None = None
    jwt_audience: str = "authenticated"

    cors_origins: list[str] = ["http://localhost:3000"]

    # Free-tier guardrail: how many projects one user may start per UTC day.
    daily_project_limit: int = 3

    # Worker tuning
    worker_poll_seconds: float = 1.0
    job_lock_timeout_seconds: int = 600


@lru_cache
def get_settings() -> Settings:
    return Settings()
