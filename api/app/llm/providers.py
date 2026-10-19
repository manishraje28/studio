import asyncio
import time
from dataclasses import dataclass, field

from app.config import Settings


@dataclass
class Provider:
    """An OpenAI-compatible chat completions endpoint."""

    name: str
    base_url: str
    model: str
    api_key: str | None = None
    # Free tiers limit requests per minute; we space calls out instead of hitting 429s.
    rpm: int = 30
    extra_headers: dict[str, str] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)
    _next_slot: float = field(default=0.0, repr=False)

    async def wait_turn(self) -> None:
        """Simple per-process limiter: at most `rpm` requests per minute, evenly spaced."""
        async with self._lock:
            now = time.monotonic()
            delay = self._next_slot - now
            self._next_slot = max(now, self._next_slot) + 60 / self.rpm
        if delay > 0:
            await asyncio.sleep(delay)


def build_providers(settings: Settings) -> list[Provider]:
    """Providers in llm_chain order, skipping any that need a key we don't have."""
    known = {
        "gemini": Provider(
            "gemini",
            "https://generativelanguage.googleapis.com/v1beta/openai",
            settings.gemini_model,
            settings.gemini_api_key,
            rpm=10,
        ),
        "groq": Provider("groq", "https://api.groq.com/openai/v1", settings.groq_model, settings.groq_api_key, rpm=30),
        "openrouter": Provider(
            "openrouter",
            "https://openrouter.ai/api/v1",
            settings.openrouter_model,
            settings.openrouter_api_key,
            rpm=20,
            extra_headers={"X-Title": "Studio"},
        ),
        "ollama": Provider("ollama", settings.ollama_base_url, settings.ollama_model, None, rpm=600),
    }
    chain = []
    for name in settings.llm_chain:
        p = known.get(name)
        if p is None:
            raise ValueError(f"Unknown LLM provider '{name}'. Known: {', '.join(known)}")
        if p.api_key or name == "ollama":
            chain.append(p)
    return chain
