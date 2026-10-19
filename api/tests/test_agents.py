import json

import httpx
import pytest
from sqlalchemy import select, update

from app import queue
from app.agents import pipeline
from app.agents.webfetch import FetchError, _assert_public, fetch_page
from app.db import SessionLocal
from app.events import since
from app.llm import LLMClient, Provider
from app.models import Artifact, Brief, Job, JobStatus, Project, ProjectStatus
from app.worker import run_one

RESEARCH = {
    "summary": "A small café in Pune known for filter coffee.",
    "audiences": ["students", "remote workers"],
    "what_customers_value": ["quiet corners", "strong coffee"],
    "differentiators": ["South Indian filter coffee"],
    "tone_words": ["warm", "unhurried"],
    "facts": [{"claim": "Serves filter coffee", "source": "brief"}],
    "open_questions": ["Opening hours?"],
}
STRATEGY = {
    "positioning": "For students in Pune who want a calm place to read.",
    "primary_audience": "students",
    "primary_action": {"label": "Reserve a table", "why": "Weekends are busy"},
    "messaging_pillars": ["coffee", "calm", "community"],
    "pages": [
        {"slug": "", "title": "Home", "goal": "Get a feel", "sections": ["Hero", "Visit"]},
        {"slug": "menu", "title": "Menu", "goal": "See prices", "sections": ["Coffee", "Food"]},
        {"slug": "visit", "title": "Visit", "goal": "Find us", "sections": ["Map", "Hours"]},
    ],
    "seo_keywords": ["café pune", "filter coffee", "study café"],
}


@pytest.fixture
def fake_llm(monkeypatch):
    """Answers with RESEARCH or STRATEGY depending on which agent is asking; records request bodies."""
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        out = RESEARCH if "Researcher" in body["messages"][0]["content"] else STRATEGY
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(out)}}]})

    client = LLMClient(
        [Provider("fake", "https://fake.test/v1", "fake-model", "k", rpm=6000)],
        SessionLocal,
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        daily_call_limit=100,
    )
    monkeypatch.setattr(pipeline, "get_llm", lambda: client)
    return requests


async def make_project(session, user_id, **kw):
    project = Project(owner_id=user_id, business_name="Kaapi House", business_type="café", city="Pune", **kw)
    project.brief = Brief(answers={"tone": "warm"})
    session.add(project)
    await session.flush()
    await queue.enqueue(session, "project.kickoff", project_id=project.id)
    await session.commit()
    return project


async def drain(skip_backoff: bool = False):
    """Run jobs until none are due. With skip_backoff, retries are made due immediately."""
    while True:
        if skip_backoff:
            async with SessionLocal() as s:
                await s.execute(update(Job).where(Job.status == JobStatus.QUEUED).values(run_at=Job.created_at))
                await s.commit()
        if not await run_one(SessionLocal, "test"):
            return


async def test_full_pipeline(session, user_id, fake_llm):
    project = await make_project(session, user_id)
    await drain()

    await session.refresh(project)
    assert project.status == ProjectStatus.DESIGN
    arts = {a.kind: a for a in await session.scalars(select(Artifact).where(Artifact.project_id == project.id))}
    assert set(arts) == {"research", "strategy"}
    assert arts["strategy"].content["primary_action"]["label"] == "Reserve a table"
    agents = [e.agent for e in await since(session, project.id)]
    assert agents[0] == "Producer" and "Researcher" in agents and "Strategist" in agents
    # The strategist sees the research file, and the brief is wrapped as data.
    strategy_prompt = fake_llm[-1]["messages"][-1]["content"]
    assert "<research>" in strategy_prompt and "filter coffee" in strategy_prompt and "<brief>" in strategy_prompt


async def test_unreachable_website_does_not_stop_research(session, user_id, fake_llm, monkeypatch):
    async def broken(_url):
        raise FetchError("HTTP 500")

    monkeypatch.setattr(pipeline.Researcher.__init__, "__defaults__", (broken,))
    project = await make_project(session, user_id, website_url="https://kaapi.example")
    await drain()

    await session.refresh(project)
    assert project.status == ProjectStatus.DESIGN
    msgs = [e.message for e in await since(session, project.id)]
    assert any("Could not read the website (HTTP 500)" in m for m in msgs)


async def test_failing_step_marks_project_failed(session, user_id, fake_llm, monkeypatch):
    async def boom(*_a, **_k):
        raise RuntimeError("model down")

    monkeypatch.setattr(pipeline.Researcher, "run", boom)
    project = await make_project(session, user_id)
    await drain(skip_backoff=True)

    await session.refresh(project)
    assert project.status == ProjectStatus.FAILED
    last = (await since(session, project.id))[-1]
    assert last.kind == "error" and "research step failed after 3 attempts" in last.message


async def test_artifacts_endpoint(client, auth, user_id, session, fake_llm):
    project = await make_project(session, user_id)
    await drain()
    r = await client.get(f"/projects/{project.id}/artifacts", headers=auth)
    assert r.status_code == 200 and sorted(a["kind"] for a in r.json()) == ["research", "strategy"]


async def test_dev_token_signs_in(client):
    r = await client.post("/dev/token", json={"email": "Owner@Example.com"})
    token = r.json()["access_token"]
    me = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200 and me.json()["id"] == r.json()["user_id"]
    again = await client.post("/dev/token", json={"email": "owner@example.com"})
    assert again.json()["user_id"] == r.json()["user_id"]  # same email, same user


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://localhost:8000/",
        "http://10.0.0.5/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "file:///etc/passwd",
        "ftp://example.com/",
        "http://example.com:2375/",
    ],
)
async def test_fetch_blocks_internal_targets(url):
    with pytest.raises(FetchError):
        await _assert_public(url)


async def test_fetch_extracts_text_and_rechecks_redirects(monkeypatch):
    html = (
        "<html><head><title>Kaapi House</title><meta name='description' content='Filter coffee in Pune'>"
        "<script>evil()</script></head><body><h1>Welcome</h1><p>Open daily.</p></body></html>"
    )

    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        if request.url.path == "/to-internal":
            return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
        return httpx.Response(200, html=html)

    checked = []

    async def fake_assert(url):
        checked.append(url)
        if "127.0.0.1" in url:
            raise FetchError("non-public")

    monkeypatch.setattr("app.agents.webfetch._assert_public", fake_assert)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    page = await fetch_page("https://kaapi.example/old", client)
    assert page.title == "Kaapi House" and page.description == "Filter coffee in Pune"
    assert page.headings == ["Welcome"] and "evil" not in page.text and "Open daily." in page.text
    assert checked == ["https://kaapi.example/old", "https://kaapi.example/new"]
    with pytest.raises(FetchError):
        await fetch_page("https://kaapi.example/to-internal", client)


async def test_connection_is_pinned_to_a_vetted_address(monkeypatch):
    """DNS rebinding: the early check sees a public IP, the connect-time lookup sees 127.0.0.1."""
    import app.agents.webfetch as wf

    answers = iter(["93.184.215.14", "127.0.0.1"])

    async def flipping_resolve(host):
        ip = next(answers)
        if ip.startswith("127."):
            raise FetchError(f"{host} resolves to a non-public address")
        return ip

    monkeypatch.setattr(wf, "_resolve_public", flipping_resolve)
    with pytest.raises(FetchError, match="non-public"):
        await fetch_page("http://rebind.example/")


async def test_public_backend_refuses_loopback():
    from app.agents.webfetch import public_client

    async with public_client() as c:
        with pytest.raises(httpx.ConnectError, match="non-public"):
            await c.get("http://127.0.0.1:80/")


async def test_fetch_refuses_compressed_and_slow_pages(monkeypatch):
    import asyncio

    import app.agents.webfetch as wf

    async def ok(_url):
        return None

    monkeypatch.setattr(wf, "_assert_public", ok)

    def gz(request):
        return httpx.Response(200, headers={"content-type": "text/html", "content-encoding": "gzip"}, content=b"x")

    with pytest.raises(FetchError, match="compressed"):
        await fetch_page("https://bomb.example/", httpx.AsyncClient(transport=httpx.MockTransport(gz)))

    async def slow(request):
        await asyncio.sleep(5)
        return httpx.Response(200, html="<p>late</p>")

    monkeypatch.setattr(wf, "TOTAL_DEADLINE", 0.2)
    with pytest.raises(FetchError, match="longer than"):
        await fetch_page("https://slow.example/", httpx.AsyncClient(transport=httpx.MockTransport(slow)))
