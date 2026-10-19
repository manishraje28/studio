import json
import sys
import uuid

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
from tests.conftest import make_token

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


STYLE = {
    "mood": "Calm and bookish, like a corner table on a slow Sunday.",
    "palette": {
        "background": "#f6efe3",
        "surface": "#fbf7f0",
        "ink": "#2b1d14",
        "muted": "#6b5847",
        "accent": "#8a3b1c",
        "accent_ink": "#fff8ef",
    },
    "typography": {
        "heading_font": "Fraunces",
        "body_font": "Inter Tight",
        "heading_style": "italic accents",
        "why": "Bookish serif with a plain body face.",
    },
    "signature_ideas": [
        {"name": "Menu as a library card", "description": "Menu set on a lined card", "why_it_fits": "reading corner"}
    ],
    "imagery": "The owner's own photos of the coffee and the shelves.",
    "layout_notes": ["Generous margins", "One column on phones"],
    "avoid": ["stock photos", "neon colours"],
}


def page_copy(slug: str) -> dict:
    return {
        "slug": slug,
        "seo_title": "Kaapi House, filter coffee in Pune",
        "meta_description": "Filter coffee and a reading corner in Pune.",
        "sections": [
            {
                "section": "Hero",
                "heading": "Filter coffee, slowly",
                "body": "Open [opening hours].",
                "cta_label": "Reserve a table",
            }
        ],
    }


@pytest.fixture
def fake_llm(monkeypatch):
    """Answers with RESEARCH or STRATEGY depending on which agent is asking; records request bodies."""
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        system = body["messages"][0]["content"]
        if "Researcher" in system:
            out = RESEARCH
        elif "Strategist" in system:
            out = STRATEGY
        elif "Art director" in system:
            out = STYLE
        elif "Photo researcher" in system:
            out = {"queries": ["coffee cup", "cafe interior", "bookshelf"]}
        elif "QA critic" in system:
            out = {
                "specificity": 7,
                "summary": "Mostly specific.",
                "generic_lines": [
                    {
                        "page": "home",
                        "text": "Quality coffee",
                        "why": "Any café",
                        "suggestion": "Filter coffee brewed in brass",
                    }
                ],
            }
        elif "Developer" in system:
            out = {"pages": [{"slug": "", "blocks": ["hero_split"]}, {"slug": "menu", "blocks": ["cards"]}]}
        else:
            out = page_copy("menu")
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(out)}}]})

    client = LLMClient(
        [Provider("fake", "https://fake.test/v1", "fake-model", "k", rpm=6000)],
        SessionLocal,
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        daily_call_limit=100,
    )
    monkeypatch.setattr(pipeline, "get_llm", lambda: client)

    async def fake_stock(queries):
        from app.site.images import Photo

        return [
            Photo(url=f"https://img.test/{i}.jpg", alt=q, credit=f"Photo {i} by Someone, CC BY 2.0", source="openverse")
            for i, q in enumerate(queries)
        ]

    monkeypatch.setattr(pipeline, "search_stock", fake_stock)
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
    assert project.status == ProjectStatus.AWAITING_APPROVAL
    arts = {a.kind: a for a in await session.scalars(select(Artifact).where(Artifact.project_id == project.id))}
    assert set(arts) == {"research", "strategy", "style"}
    assert arts["strategy"].content["primary_action"]["label"] == "Reserve a table"
    agents = [e.agent for e in await since(session, project.id)]
    assert agents[0] == "Producer" and "Researcher" in agents and "Strategist" in agents
    # The strategist sees the research file, and the brief is wrapped as data.
    strategy_prompt = next(b for b in fake_llm if "Strategist" in b["messages"][0]["content"])["messages"][-1][
        "content"
    ]
    assert "<research>" in strategy_prompt and "filter coffee" in strategy_prompt and "<brief>" in strategy_prompt


async def test_unreachable_website_does_not_stop_research(session, user_id, fake_llm, monkeypatch):
    async def broken(_url):
        raise FetchError("HTTP 500")

    monkeypatch.setattr(pipeline.Researcher.__init__, "__defaults__", (broken,))
    project = await make_project(session, user_id, website_url="https://kaapi.example")
    await drain()

    await session.refresh(project)
    assert project.status == ProjectStatus.AWAITING_APPROVAL
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
    assert r.status_code == 200 and sorted(a["kind"] for a in r.json()) == ["research", "strategy", "style"]


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


async def test_approval_gate(client, auth, user_id, session, fake_llm):
    project = await make_project(session, user_id)
    url = f"/projects/{project.id}/direction"
    # Nothing to approve yet.
    assert (await client.post(url, json={"decision": "approve"}, headers=auth)).status_code == 409
    await drain()

    # Revise needs a real note, then re-runs the art director with it.
    assert (await client.post(url, json={"decision": "revise", "note": ""}, headers=auth)).status_code == 422
    r = await client.post(url, json={"decision": "revise", "note": "Warmer, less brown please"}, headers=auth)
    assert r.json()["status"] == "design"
    await drain()
    art_prompt = [b for b in fake_llm if "Art director" in b["messages"][0]["content"]][-1]["messages"][-1]["content"]
    assert "<owner_feedback>Warmer, less brown please</owner_feedback>" in art_prompt
    styles = list(await session.scalars(select(Artifact).where(Artifact.kind == "style")))
    assert sorted(a.version for a in styles) == [1, 2]

    # Strangers cannot approve.
    from tests.conftest import make_token

    other = {"Authorization": f"Bearer {make_token()}"}
    assert (await client.post(url, json={"decision": "approve"}, headers=other)).status_code == 404

    r = await client.post(url, json={"decision": "approve"}, headers=auth)
    assert r.json()["status"] == "copy"
    assert (await client.post(url, json={"decision": "approve"}, headers=auth)).status_code == 409  # only once
    await drain()

    await session.refresh(project)
    assert project.status == ProjectStatus.PREVIEW
    copy = await session.scalar(select(Artifact).where(Artifact.kind == "copy"))
    assert len(copy.content["pages"]) == 3  # one per planned page
    msgs = [e.message for e in await since(session, project.id)]
    assert any("Writing Menu (2 of 3)" in m for m in msgs)
    assert any("marked [like this]" in m for m in msgs)


async def test_copy_retry_resumes_after_finished_pages(client, auth, user_id, session, fake_llm, monkeypatch):
    project = await make_project(session, user_id)
    await drain()
    await client.post(f"/projects/{project.id}/direction", json={"decision": "approve"}, headers=auth)

    real = pipeline.Copywriter.run_page
    calls = []

    async def flaky(self, ctx, page):
        calls.append(page["slug"])
        if page["slug"] == "visit" and calls.count("visit") == 1:
            raise RuntimeError("rate limited")
        return await real(self, ctx, page)

    monkeypatch.setattr(pipeline.Copywriter, "run_page", flaky)
    await drain(skip_backoff=True)
    # Home and menu were written once; only the failed page was retried.
    assert calls == ["", "menu", "visit", "visit"]
    await session.refresh(project)
    assert project.status == ProjectStatus.PREVIEW


async def test_revisions_are_capped(client, auth, user_id, session, fake_llm, monkeypatch):
    from app.routers import projects as projects_router

    monkeypatch.setattr(projects_router, "MAX_STYLE_VERSIONS", 2)
    project = await make_project(session, user_id)
    await drain()
    url = f"/projects/{project.id}/direction"
    assert (
        await client.post(url, json={"decision": "revise", "note": "warmer please"}, headers=auth)
    ).status_code == 200
    await drain()
    r = await client.post(url, json={"decision": "revise", "note": "even warmer"}, headers=auth)
    assert r.status_code == 429
    assert (await client.post(url, json={"decision": "approve"}, headers=auth)).status_code == 200


async def test_preview(client, auth, user_id, session, fake_llm, monkeypatch):
    evil = page_copy("")
    evil["sections"][0]["heading"] = "<script>alert(1)</script>Fresh coffee"
    monkeypatch.setattr(sys.modules[__name__], "page_copy", lambda slug: {**evil, "slug": slug})
    project = await make_project(session, user_id)
    await drain()
    await client.post(f"/projects/{project.id}/direction", json={"decision": "approve"}, headers=auth)
    await drain()

    path = (await client.get(f"/projects/{project.id}/preview", headers=auth)).json()["path"]
    r = await client.get(path)
    assert r.status_code == 200, r.text
    assert "text/html" in r.headers["content-type"]
    assert "default-src 'none'" in r.headers["content-security-policy"]
    html = r.text
    assert "<script>" not in html and "&lt;script&gt;" in html  # copy is escaped
    arts = {a["kind"]: a for a in (await client.get(f"/projects/{project.id}/artifacts", headers=auth)).json()}
    assert arts["qa"]["content"]["review"]["specificity"] == 7 and 0 <= arts["qa"]["content"]["score"] <= 100
    assert '<span class="ph">[opening hours]</span>' in html  # placeholders highlighted
    assert "Fraunces" in html and "#8a3b1c" in html  # style tile applied
    assert f"/preview/{project.id}/menu?t=" in html  # nav links keep the token
    # Wrong or missing token, or another project's token, gets nothing.
    assert (await client.get(f"/preview/{project.id}/")).status_code == 404
    assert (await client.get(path.replace("t=", "t=x"))).status_code == 404
    assert (
        await client.get(f"/projects/{project.id}/preview", headers={"Authorization": "Bearer x"})
    ).status_code == 401


async def test_context_never_mixes_projects(session, user_id):
    a = Project(owner_id=user_id, business_name="A Cafe", business_type="cafe")
    b = Project(owner_id=uuid.uuid4(), business_name="B Clinic", business_type="clinic")
    session.add_all([a, b])
    await session.flush()
    await pipeline.save_artifact(session, a, "research", "Researcher", {"owner": "A"})
    await pipeline.save_artifact(session, b, "research", "Researcher", {"owner": "B"})
    await session.commit()
    ctx_a = await pipeline.load_context(session, a)
    ctx_b = await pipeline.load_context(session, b)
    assert ctx_a.artifacts == {"research": {"owner": "A"}}
    assert ctx_b.artifacts == {"research": {"owner": "B"}}


async def test_owner_fills_details(client, auth, user_id, session, fake_llm):
    project = await make_project(session, user_id)
    await drain()
    await client.post(f"/projects/{project.id}/direction", json={"decision": "approve"}, headers=auth)
    await drain()
    url = f"/projects/{project.id}/details"

    got = (await client.get(url, headers=auth)).json()
    assert got["details"] == [{"label": "opening hours", "value": ""}] and got["questions"] == ["Opening hours?"]
    assert (await client.put(url, json={"values": {"made up": "x"}}, headers=auth)).status_code == 422

    r = await client.put(url, json={"values": {"opening hours": "7am to 9pm, <b>daily</b>"}}, headers=auth)
    assert r.json()["details"][0]["value"] == "7am to 9pm, <b>daily</b>"

    path = (await client.get(f"/projects/{project.id}/preview", headers=auth)).json()["path"]
    html = (await client.get(path)).text
    assert "Open 7am to 9pm, &lt;b&gt;daily&lt;/b&gt;." in html  # filled and still escaped
    assert "[opening hours]" not in html
    other = {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}
    assert (await client.get(url, headers=other)).status_code == 404


def png_bytes(w=1200, h=800, fmt="PNG") -> bytes:
    import io as _io

    from PIL import Image

    buf = _io.BytesIO()
    Image.new("RGB", (w, h), (200, 120, 80)).save(buf, fmt)
    return buf.getvalue()


async def built_project(client, auth, session, user_id):
    project = await make_project(session, user_id)
    await drain()
    await client.post(f"/projects/{project.id}/direction", json={"decision": "approve"}, headers=auth)
    await drain()
    return project


async def test_photos_upload_preview_and_rebuild(client, auth, user_id, session, fake_llm):
    project = await built_project(client, auth, session, user_id)
    base = f"/projects/{project.id}/photos"

    bad = await client.post(base, files={"file": ("x.jpg", b"not an image", "image/jpeg")}, headers=auth)
    assert bad.status_code == 422
    r = await client.post(base, files={"file": ("shop_front.png", png_bytes(3000, 2000), "image/png")}, headers=auth)
    assert r.status_code == 201
    photo = r.json()[0]
    assert photo["alt"] == "shop front" and photo["width"] <= 1800  # resized

    # The media URL needs the signed token.
    assert (await client.get(photo["url"])).status_code == 200
    assert (await client.get(photo["url"].split("?")[0])).status_code == 404

    path = (await client.get(f"/projects/{project.id}/preview", headers=auth)).json()["path"]
    html = (await client.get(path)).text
    assert photo["url"].replace("&", "&amp;") in html or photo["url"] in html  # owner photo used first
    stock = await session.scalar(select(Artifact).where(Artifact.project_id == project.id, Artifact.kind == "stock"))
    assert len(stock.content["photos"]) == 3 and stock.content["queries"][0] == "coffee cup"

    r = await client.post(f"/projects/{project.id}/rebuild", headers=auth)
    assert r.json()["status"] == "building"
    await drain()
    await session.refresh(project)
    assert project.status == ProjectStatus.PREVIEW

    assert (await client.delete(f"{base}/{photo['name']}", headers=auth)).json() == []
    other = {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}
    assert (await client.get(base, headers=other)).status_code == 404


def test_oversized_photo_rejected_before_decode(monkeypatch):
    from PIL import Image

    from app.site.images import UploadError, save_upload

    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000 * 700)  # smaller than the 1200x800 test image
    with pytest.raises(UploadError, match="too large"):
        save_upload(uuid.uuid4(), png_bytes())


async def test_export_zip_and_publish(client, auth, user_id, session, fake_llm, monkeypatch):
    import io as _io
    import zipfile

    project = await built_project(client, auth, session, user_id)
    await client.post(
        f"/projects/{project.id}/photos", files={"file": ("front.png", png_bytes(), "image/png")}, headers=auth
    )

    r = await client.get(f"/projects/{project.id}/export", headers=auth)
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    z = zipfile.ZipFile(_io.BytesIO(r.content))
    names = z.namelist()
    assert {"index.html", "menu/index.html", "visit/index.html", "404.html", "README.md"} <= set(names)
    assets = [n for n in names if n.startswith("assets/")]
    assert len(assets) == 1  # the owner's photo is copied in; unreachable stock photos are dropped
    home = z.read("index.html").decode()
    assert f'src="/{assets[0]}"' in home and 'href="/menu/"' in home and "/preview/" not in home

    calls = {}

    async def fake_deploy(files, name, account_id, token):
        calls.update(files=files, name=name)
        return {"url": f"https://{name}.pages.dev", "deployment_url": "https://abc.x.pages.dev", "id": "d1"}

    monkeypatch.setattr(pipeline, "deploy", fake_deploy)
    monkeypatch.setattr(
        "app.config.get_settings",
        lambda: type("S", (), {"cloudflare_account_id": "acc", "cloudflare_api_token": "tok"})(),
    )
    r = await client.post(f"/projects/{project.id}/publish", headers=auth)
    assert r.status_code == 200
    assert (await client.post(f"/projects/{project.id}/publish", headers=auth)).status_code == 409  # one at a time
    await drain()
    await session.refresh(project)
    assert project.status == ProjectStatus.LIVE
    assert calls["name"].startswith("kaapi-house-") and "index.html" in calls["files"]
    msgs = [e.message for e in await since(session, project.id)]
    assert any("Your site is live at https://kaapi-house-" in m for m in msgs)
    other = {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}
    assert (await client.post(f"/projects/{project.id}/publish", headers=other)).status_code == 404
    assert (await client.get(f"/projects/{project.id}/export", headers=other)).status_code == 404


async def test_revisions_undo_and_manual_edits(client, auth, user_id, session, fake_llm, monkeypatch):
    from app.agents import revisions
    from app.agents.copywriting import SectionCopy

    project = await built_project(client, auth, session, user_id)
    base = f"/projects/{project.id}"

    async def fake_plan(self, ctx, request, page, section_index):
        return revisions.RevisionPlan(
            summary="Rewrite the hero and drop the menu's last section",
            steps=[revisions.ChangeStep(op="edit_copy", page="", section_index=0, instruction=request)],
        )

    async def fake_rewrite(llm, ctx, page, section, instruction):
        return SectionCopy(section="Hero", heading="Bridal makeup in Panaji", body="Book a trial.", cta_label="Book")

    monkeypatch.setattr(revisions.Producer, "plan", fake_plan)
    monkeypatch.setattr(revisions, "rewrite_section", fake_rewrite)

    r = await client.post(f"{base}/revisions", json={"request": "Mention bridal makeup in the hero"}, headers=auth)
    assert r.json()["status"] == "revising"
    assert (await client.post(f"{base}/revisions", json={"request": "Another change"}, headers=auth)).status_code == 409
    await drain()
    await session.refresh(project)
    assert project.status == ProjectStatus.PREVIEW

    copy = (await client.get(f"{base}/artifacts", headers=auth)).json()
    latest_copy = max((a for a in copy if a["kind"] == "copy"), key=lambda a: a["version"])
    assert latest_copy["content"]["pages"][0]["sections"][0]["heading"] == "Bridal makeup in Panaji"
    revs = (await client.get(f"{base}/revisions", headers=auth)).json()
    assert (
        revs[0]["summary"].startswith("Rewrite the hero") and revs[0]["after"]["copy"] == revs[0]["before"]["copy"] + 1
    )

    # Undo puts the old text back as a new version.
    r = await client.post(f"{base}/revisions/{revs[0]['version']}/undo", headers=auth)
    assert r.status_code == 200
    arts = (await client.get(f"{base}/artifacts", headers=auth)).json()
    restored = max((a for a in arts if a["kind"] == "copy"), key=lambda a: a["version"])
    assert restored["content"]["pages"][0]["sections"][0]["heading"] == "Filter coffee, slowly"

    # Manual edits: dashes cleaned, hype refused, strangers locked out.
    r = await client.put(f"{base}/copy/:0", json={"heading": "Coffee — slowly", "body": "Open daily."}, headers=auth)
    assert r.status_code == 200
    arts = (await client.get(f"{base}/artifacts", headers=auth)).json()
    edited = max((a for a in arts if a["kind"] == "copy"), key=lambda a: a["version"])
    assert edited["content"]["pages"][0]["sections"][0]["heading"] == "Coffee, slowly"
    bad = await client.put(f"{base}/copy/:0", json={"heading": "Elevate your mornings", "body": ""}, headers=auth)
    assert bad.status_code == 422
    assert (await client.put(f"{base}/copy/:9", json={"heading": "x"}, headers=auth)).status_code == 404
    other = {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}
    assert (await client.post(f"{base}/revisions", json={"request": "hack it"}, headers=other)).status_code == 404


async def test_revision_plan_ops_apply(session, user_id, fake_llm, monkeypatch):
    from app.agents import revisions
    from app.agents.copywriting import SectionCopy

    project = await make_project(session, user_id)
    await drain()
    await queue.enqueue(session, "agent.copy", project_id=project.id)
    await session.commit()
    await drain()
    ctx = await pipeline.load_context(session, project)

    async def fake_rewrite(llm, ctx, page, section, instruction):
        return SectionCopy(section="Offer", heading="Diwali offer", body="10% off sweets.", cta_label=None)

    monkeypatch.setattr(revisions, "rewrite_section", fake_rewrite)
    plan = revisions.RevisionPlan(
        summary="x",
        steps=[
            revisions.ChangeStep(op="add_section", page="menu", instruction="Diwali offer"),
            revisions.ChangeStep(op="remove_page", page="visit", instruction="not needed"),
            revisions.ChangeStep(op="remove_page", page="", instruction="must be ignored"),
        ],
    )
    changed, log = await revisions.apply_plan(session, pipeline.get_llm(), project, ctx, plan)
    slugs = [p["slug"] for p in changed["copy"]["pages"]]
    assert slugs == ["", "menu"]  # visit removed, home kept
    assert changed["copy"]["pages"][1]["sections"][-1]["heading"] == "Diwali offer"
    assert "layout" in changed and len(log) == 2


async def test_revision_budget_and_failure_recovery(client, auth, user_id, session, fake_llm, monkeypatch):
    from app.agents import revisions
    from app.agents.copywriting import SectionCopy

    project = await built_project(client, auth, session, user_id)
    calls = []

    async def counting_rewrite(llm, ctx, page, section, instruction):
        calls.append(1)
        return SectionCopy(section="x", heading="New", body="", cta_label=None)

    monkeypatch.setattr(revisions, "rewrite_section", counting_rewrite)
    monkeypatch.setattr(revisions, "MAX_CALLS_PER_REVISION", 2)
    ctx = await pipeline.load_context(session, project)
    plan = revisions.RevisionPlan(
        summary="x",
        steps=[
            revisions.ChangeStep(op="edit_copy", page="", instruction="all"),
            revisions.ChangeStep(op="edit_copy", page="menu", instruction="all"),
            revisions.ChangeStep(op="add_section", page="menu", instruction="more"),
        ],
    )
    _, log = await revisions.apply_plan(session, pipeline.get_llm(), project, ctx, plan)
    assert len(calls) == 2 and any("Stopped early" in line for line in log)

    async def broken_plan(self, *a):
        raise RuntimeError("model down")

    monkeypatch.setattr(revisions.Producer, "plan", broken_plan)
    await client.post(f"/projects/{project.id}/revisions", json={"request": "Change the hero"}, headers=auth)
    await drain(skip_backoff=True)
    await session.refresh(project)
    assert project.status == ProjectStatus.PREVIEW  # a failed change does not break the project
    msgs = [e.message for e in await since(session, project.id)]
    assert any("could not be made" in m for m in msgs)
