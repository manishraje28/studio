from functools import lru_cache

import httpx

from app.config import get_settings
from app.db import SessionLocal
from app.llm.client import AllProvidersFailed, BudgetExceeded, Completion, LLMClient, LLMError
from app.llm.providers import Provider, build_providers

__all__ = [
    "AllProvidersFailed",
    "BudgetExceeded",
    "Completion",
    "LLMClient",
    "LLMError",
    "Provider",
    "get_llm",
]


@lru_cache
def get_llm() -> LLMClient:
    settings = get_settings()
    return LLMClient(
        build_providers(settings),
        SessionLocal,
        httpx.AsyncClient(timeout=settings.llm_timeout_seconds),
        daily_call_limit=settings.llm_daily_call_limit,
    )
