import uuid

from sqlalchemy import select

from app.models import Job, JobStatus
from tests.conftest import make_token

BRIEF = {"business_name": "Kaapi House", "business_type": "café", "city": "Pune", "answers": {"tone": "warm"}}


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


async def test_requires_auth(client):
    assert (await client.get("/projects")).status_code == 401
    assert (await client.post("/projects", json=BRIEF)).status_code == 401


async def test_rejects_bad_tokens(client):
    for token in [make_token(expired=True), make_token(secret="wrong-secret-wrong-secret-wrong-secret"), "nope"]:
        r = await client.get("/projects", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401


async def test_me(client, auth, user_id):
    r = await client.get("/me", headers=auth)
    assert r.json()["id"] == str(user_id)


async def test_create_project_enqueues_kickoff(client, auth, session):
    r = await client.post("/projects", json=BRIEF, headers=auth)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "briefed" and body["business_name"] == "Kaapi House"

    jobs = list(await session.scalars(select(Job)))
    assert [(j.kind, j.status, str(j.project_id)) for j in jobs] == [("project.kickoff", JobStatus.QUEUED, body["id"])]


async def test_validation(client, auth):
    r = await client.post("/projects", json={**BRIEF, "business_name": "x"}, headers=auth)
    assert r.status_code == 422
    r = await client.post("/projects", json={**BRIEF, "website_url": "not a url"}, headers=auth)
    assert r.status_code == 422


async def test_owners_only_see_their_projects(client, auth):
    created = (await client.post("/projects", json=BRIEF, headers=auth)).json()
    stranger = {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}

    assert (await client.get("/projects", headers=stranger)).json() == []
    assert (await client.get(f"/projects/{created['id']}", headers=stranger)).status_code == 404
    assert (await client.get(f"/projects/{created['id']}/events", headers=stranger)).status_code == 404
    assert (await client.get(f"/projects/{created['id']}", headers=auth)).status_code == 200


async def test_daily_limit(client, auth):
    for _ in range(3):
        assert (await client.post("/projects", json=BRIEF, headers=auth)).status_code == 201
    r = await client.post("/projects", json=BRIEF, headers=auth)
    assert r.status_code == 429
    # The limit is per user.
    other = {"Authorization": f"Bearer {make_token(uuid.uuid4())}"}
    assert (await client.post("/projects", json=BRIEF, headers=other)).status_code == 201


async def test_daily_limit_holds_under_parallel_requests(client, auth):
    import asyncio

    results = await asyncio.gather(*(client.post("/projects", json=BRIEF, headers=auth) for _ in range(8)))
    codes = sorted(r.status_code for r in results)
    assert codes.count(201) == 3 and codes.count(429) == 5


async def test_brief_answers_are_bounded(client, auth):
    ok = {**BRIEF, "answers": {"tone": "warm", "pages": ["Home", "Menu"]}}
    assert (await client.post("/projects", json=ok, headers=auth)).status_code == 201
    for bad in [
        {"nested": {"a": 1}},
        {"tone": "x" * 2001},
        {f"k{i}": "v" for i in range(31)},
        {"Bad Key": "v"},
        {"pages": ["p"] * 21},
    ]:
        r = await client.post("/projects", json={**BRIEF, "answers": bad}, headers=auth)
        assert r.status_code == 422, bad
