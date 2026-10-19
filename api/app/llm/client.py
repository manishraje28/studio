"""One client for every free model provider.

complete()       plain text from the first provider in the chain that answers
complete_json()  same, parsed and validated into a Pydantic model, with one repair round

Per provider: wait for a rate-limit slot, retry 429/5xx/timeouts with backoff (honouring
Retry-After), then fall through to the next provider. Every attempt is logged to llm_calls,
which also backs a hard daily call budget.
"""

import asyncio
import json
import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.llm.providers import Provider
from app.models import LLMCall

log = logging.getLogger("studio.llm")

Message = dict[str, str]
RETRYABLE = {408, 409, 425, 429, 500, 502, 503, 504}


class LLMError(Exception):
    pass


class BudgetExceeded(LLMError):
    pass


class AllProvidersFailed(LLMError):
    pass


@dataclass
class Completion:
    text: str
    provider: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMClient:
    def __init__(
        self,
        providers: list[Provider],
        sessions: async_sessionmaker[AsyncSession],
        http: httpx.AsyncClient,
        *,
        daily_call_limit: int,
        attempts_per_provider: int = 3,
        rate_limit_attempts: int = 6,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.providers = providers
        self.sessions = sessions
        self.http = http
        self.daily_call_limit = daily_call_limit
        self.attempts_per_provider = attempts_per_provider
        # Free tiers return 429 often and recover within seconds, so they get more patience.
        self.rate_limit_attempts = rate_limit_attempts
        self.sleep = sleep

    async def calls_today(self) -> int:
        start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        async with self.sessions() as s:
            return await s.scalar(select(func.count()).select_from(LLMCall).where(LLMCall.created_at >= start)) or 0

    async def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 2048,
        json_mode: bool = False,
        project_id: uuid.UUID | None = None,
        agent: str | None = None,
    ) -> Completion:
        if not self.providers:
            raise LLMError("No AI provider configured. Set GEMINI_API_KEY, GROQ_API_KEY or OPENROUTER_API_KEY.")
        if await self.calls_today() >= self.daily_call_limit:
            raise BudgetExceeded(f"Daily limit of {self.daily_call_limit} model calls reached")

        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        errors: list[str] = []
        for provider in self.providers:
            body: dict[str, Any] = {
                "model": provider.model,
                "messages": msgs,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if json_mode:
                body["response_format"] = {"type": "json_object"}

            attempt = 0
            rate_limited = 0
            while True:
                attempt += 1
                await provider.wait_turn()
                started = time.monotonic()
                status: int | None = None
                try:
                    resp = await self.http.post(
                        f"{provider.base_url.rstrip('/')}/chat/completions",
                        json=body,
                        headers={
                            **({"Authorization": f"Bearer {provider.api_key}"} if provider.api_key else {}),
                            **provider.extra_headers,
                        },
                    )
                    status = resp.status_code
                    if status == 200:
                        data = resp.json()
                        text = data["choices"][0]["message"]["content"] or ""
                        usage = data.get("usage") or {}
                        result = Completion(
                            text,
                            provider.name,
                            provider.model,
                            usage.get("prompt_tokens"),
                            usage.get("completion_tokens"),
                        )
                        await self._log(provider, project_id, agent, started, True, status, result)
                        return result
                    error = f"HTTP {status}: {resp.text[:300]}"
                    retry_after = _retry_after(resp)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    error, retry_after = f"{type(exc).__name__}: {exc}", None
                except (KeyError, IndexError, ValueError) as exc:
                    error, retry_after = f"Malformed response: {exc}", None

                await self._log(provider, project_id, agent, started, False, status, error=error)
                errors.append(f"{provider.name}#{attempt}: {error}")
                log.warning("llm %s attempt %s failed: %s", provider.name, attempt, error)
                # Auth errors, bad model names and the like will not fix themselves: next provider.
                if status is not None and status not in RETRYABLE:
                    break
                if status == 429:
                    rate_limited += 1
                    if rate_limited >= self.rate_limit_attempts:
                        break
                elif attempt - rate_limited >= self.attempts_per_provider:
                    break
                await self.sleep(min(retry_after or 2 ** min(attempt, 4), 20))

        raise AllProvidersFailed("; ".join(errors))

    async def complete_json[T: BaseModel](
        self, schema: type[T], messages: list[Message], *, system: str | None = None, **kwargs: Any
    ) -> T:
        """Ask for JSON matching `schema`. If the reply does not validate, send the error back once."""
        instructions = (
            "Reply with a single JSON object and nothing else. It must match this JSON schema:\n"
            + json.dumps(schema.model_json_schema())
        )
        system = f"{system}\n\n{instructions}" if system else instructions
        first = await self.complete(messages, system=system, json_mode=True, **kwargs)
        try:
            return schema.model_validate_json(extract_json(first.text))
        except (ValidationError, ValueError) as exc:
            repair = messages + [
                {"role": "assistant", "content": first.text},
                {"role": "user", "content": f"That JSON was invalid: {exc}. Reply again with only the corrected JSON."},
            ]
            second = await self.complete(repair, system=system, json_mode=True, **kwargs)
            return schema.model_validate_json(extract_json(second.text))

    async def _log(
        self,
        provider: Provider,
        project_id: uuid.UUID | None,
        agent: str | None,
        started: float,
        ok: bool,
        status: int | None,
        result: Completion | None = None,
        error: str | None = None,
    ) -> None:
        async with self.sessions() as s:
            s.add(
                LLMCall(
                    project_id=project_id,
                    agent=agent,
                    provider=provider.name,
                    model=provider.model,
                    ok=ok,
                    status_code=status,
                    latency_ms=int((time.monotonic() - started) * 1000),
                    prompt_tokens=result.prompt_tokens if result else None,
                    completion_tokens=result.completion_tokens if result else None,
                    error=error[:2000] if error else None,
                )
            )
            await s.commit()


def _retry_after(resp: httpx.Response) -> float | None:
    try:
        return float(resp.headers["retry-after"])
    except (KeyError, ValueError):
        return None


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def extract_json(text: str) -> str:
    """Models sometimes wrap JSON in code fences or add a sentence around it."""
    text = _FENCE.sub("", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end < start:
        raise ValueError("no JSON object in reply")
    return text[start : end + 1]
