from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Safe default: dev-only routes (like /dev/token) exist only when ENV=development is set explicitly.
    env: str = "production"
    database_url: str = "postgresql+asyncpg://studio:studio@localhost:54322/studio"

    # Supabase Auth. Projects with asymmetric signing keys verify through JWKS (supabase_url);
    # legacy projects and the test suite use the shared HS256 secret.
    supabase_url: str | None = None
    supabase_jwt_secret: str | None = None
    jwt_audience: str = "authenticated"

    cors_origins: list[str] = ["http://localhost:3000"]
    # Signs preview links. Falls back to SUPABASE_JWT_SECRET when unset.
    preview_secret: str | None = None

    # Free-tier guardrail: how many projects one user may start per UTC day.
    daily_project_limit: int = 3

    # AI providers. All are OpenAI-compatible and free-tier friendly. They are tried in
    # llm_chain order; providers without an API key are skipped (ollama needs none).
    llm_chain: list[str] = ["groq", "gemini", "openrouter"]
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-flash-latest"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    openrouter_api_key: str | None = None
    openrouter_model: str = "google/gemma-4-31b-it:free"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2"
    llm_timeout_seconds: float = 45
    # Hard stop on total model calls per UTC day, so a public demo cannot drain free quotas.
    llm_daily_call_limit: int = 400

    # Publishing client sites to Cloudflare Pages (free). Token needs "Cloudflare Pages: Edit".
    cloudflare_account_id: str | None = None
    cloudflare_api_token: str | None = None

    # Worker tuning
    worker_poll_seconds: float = 1.0
    job_lock_timeout_seconds: int = 600


@lru_cache
def get_settings() -> Settings:
    return Settings()
