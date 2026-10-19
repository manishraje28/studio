import json

import httpx
import pytest
from pydantic import BaseModel
from sqlalchemy import select

from app.config import Settings
from app.db import SessionLocal
from app.llm import AllProvidersFailed, BudgetExceeded, LLMClient, Provider
from app.llm.client import extract_json
from app.llm.providers import build_providers
from app.models import LLMCall


def reply(text: str, status: int = 200, headers: dict | None = None) -> httpx.Response:
    if status != 200:
        return httpx.Response(status, text=text, headers=headers)
    body = {"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 7, "completion_tokens": 3}}
    return httpx.Response(200, json=body)


def make_client(script, providers=("a", "b"), limit=100):
    """script: function(provider_host, request) -> Response. Records every request."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.host, json.loads(request.content)))
        return script(request.url.host, request)

    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)

    client = LLMClient(
        [Provider(n, f"https://{n}.test/v1", f"{n}-model", "key", rpm=6000) for n in providers],
        SessionLocal,
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        daily_call_limit=limit,
        sleep=fake_sleep,
    )
    return client, seen, sleeps


MSG = [{"role": "user", "content": "hi"}]


async def test_first_provider_answers(session):
    llm, seen, _ = make_client(lambda host, r: reply("hello"))
    out = await llm.complete(MSG, system="be brief", agent="Researcher")
    assert (out.text, out.provider, out.prompt_tokens) == ("hello", "a", 7)
    host, body = seen[0]
    assert host == "a.test" and body["model"] == "a-model" and body["messages"][0]["role"] == "system"
    calls = list(await session.scalars(select(LLMCall)))
    assert [(c.provider, c.ok, c.agent) for c in calls] == [("a", True, "Researcher")]


async def test_retries_429_honouring_retry_after():
    responses = iter([reply("slow down", 429, {"retry-after": "7"}), reply("ok")])
    llm, seen, sleeps = make_client(lambda host, r: next(responses))
    assert (await llm.complete(MSG)).text == "ok"
    assert sleeps == [7.0] and len(seen) == 2


async def test_falls_back_to_next_provider(session):
    llm, seen, sleeps = make_client(lambda host, r: reply("bad key", 401) if host == "a.test" else reply("from b"))
    out = await llm.complete(MSG)
    assert out.provider == "b" and out.text == "from b"
    assert [h for h, _ in seen] == ["a.test", "b.test"] and sleeps == []  # 401 is not retried
    oks = [(c.provider, c.ok, c.status_code) for c in await session.scalars(select(LLMCall).order_by(LLMCall.id))]
    assert oks == [("a", False, 401), ("b", True, 200)]


async def test_all_fail_raises_with_details():
    llm, seen, _ = make_client(lambda host, r: reply("down", 503))
    with pytest.raises(AllProvidersFailed) as e:
        await llm.complete(MSG)
    assert len(seen) == 6 and "a#3" in str(e.value) and "b#1" in str(e.value)


async def test_timeouts_are_retried():
    calls = {"n": 0}

    def script(host, r):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("slow", request=r)
        return reply("late but fine")

    llm, _, _ = make_client(script)
    assert (await llm.complete(MSG)).text == "late but fine"


async def test_daily_budget():
    llm, _, _ = make_client(lambda host, r: reply("x"), limit=2)
    await llm.complete(MSG)
    await llm.complete(MSG)
    with pytest.raises(BudgetExceeded):
        await llm.complete(MSG)


class Plan(BaseModel):
    pages: list[str]
    cta: str


async def test_json_mode_with_fences():
    llm, seen, _ = make_client(lambda host, r: reply('```json\n{"pages": ["Home", "Menu"], "cta": "Reserve"}\n```'))
    plan = await llm.complete_json(Plan, MSG)
    assert plan == Plan(pages=["Home", "Menu"], cta="Reserve")
    body = seen[0][1]
    assert body["response_format"] == {"type": "json_object"} and "JSON schema" in body["messages"][0]["content"]


async def test_json_repair_round():
    answers = iter([reply('{"pages": "Home"}'), reply('{"pages": ["Home"], "cta": "Call us"}')])
    llm, seen, _ = make_client(lambda host, r: next(answers))
    plan = await llm.complete_json(Plan, MSG)
    assert plan.cta == "Call us"
    repair_msgs = seen[1][1]["messages"]
    assert repair_msgs[-1]["role"] == "user" and "invalid" in repair_msgs[-1]["content"]


def test_extract_json():
    assert extract_json('Sure! {"a": 1} hope that helps') == '{"a": 1}'
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_build_providers_skips_missing_keys():
    s = Settings(llm_chain=["gemini", "groq", "ollama"], gemini_api_key=None, groq_api_key="g")
    assert [p.name for p in build_providers(s)] == ["groq", "ollama"]
    with pytest.raises(ValueError):
        build_providers(Settings(llm_chain=["nope"]))


async def test_status_endpoint(client, auth):
    r = await client.get("/llm/status", headers=auth)
    assert r.status_code == 200 and set(r.json()) == {"providers", "calls_today", "daily_limit"}
    assert "key" not in r.text.lower()


async def test_rate_limits_get_more_patience_than_errors():
    responses = iter([reply("slow", 429)] * 5 + [reply("finally")])
    llm, seen, sleeps = make_client(lambda host, r: next(responses), providers=("a",))
    assert (await llm.complete(MSG)).text == "finally"
    assert len(seen) == 6 and len(sleeps) == 5


async def test_rate_limit_attempts_are_capped():
    llm, seen, _ = make_client(lambda host, r: reply("slow", 429), providers=("a",))
    with pytest.raises(AllProvidersFailed):
        await llm.complete(MSG)
    assert len(seen) == 6


async def test_json_validate_failure_retries_without_strict_mode():
    bodies = []

    def script(host, r):
        body = json.loads(r.content)
        bodies.append(body)
        if "response_format" in body:
            return httpx.Response(400, json={"error": {"code": "json_validate_failed"}})
        return reply('{"pages": ["Home"], "cta": "Call"}')

    llm, seen, _ = make_client(script, providers=("a",))
    plan = await llm.complete_json(Plan, MSG)
    assert plan.cta == "Call" and len(seen) == 2 and "response_format" not in bodies[1]
