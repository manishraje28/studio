import asyncio
from datetime import UTC, datetime, timedelta

from app import queue
from app.db import SessionLocal
from app.events import since
from app.models import Job, JobStatus, Project, ProjectStatus
from app.worker import HANDLERS, run_one


async def test_claim_complete(session):
    job = await queue.enqueue(session, "noop", {"a": 1})
    await session.commit()

    claimed = await queue.claim(session, "w1")
    assert claimed and claimed.id == job.id
    assert claimed.status == JobStatus.RUNNING and claimed.attempts == 1 and claimed.locked_by == "w1"
    assert await queue.claim(session, "w2") is None  # nothing else due

    await queue.complete(session, claimed, {"ok": True})
    assert claimed.status == JobStatus.SUCCEEDED and claimed.result == {"ok": True}


async def test_delayed_jobs_wait(session):
    await queue.enqueue(session, "later", delay=timedelta(minutes=5))
    await session.commit()
    assert await queue.claim(session, "w1") is None


async def test_concurrent_workers_never_share_a_job(session):
    for i in range(10):
        await queue.enqueue(session, "noop", {"i": i})
    await session.commit()

    async def drain(name: str) -> list:
        got = []
        async with SessionLocal() as s:
            while job := await queue.claim(s, name):
                got.append(job.id)
        return got

    results = await asyncio.gather(*(drain(f"w{n}") for n in range(4)))
    ids = [i for r in results for i in r]
    assert len(ids) == 10 and len(set(ids)) == 10


async def test_failure_retries_with_backoff_then_fails(session):
    job = await queue.enqueue(session, "flaky", max_attempts=2)
    await session.commit()

    claimed = await queue.claim(session, "w1")
    await queue.fail(session, claimed, "boom")
    assert claimed.status == JobStatus.QUEUED and claimed.last_error == "boom"
    assert await queue.claim(session, "w1") is None  # backing off

    claimed.run_at = datetime.now(UTC)  # skip the wait
    await session.commit()
    again = await queue.claim(session, "w1")
    assert again.id == job.id and again.attempts == 2
    await queue.fail(session, again, "boom again")
    assert again.status == JobStatus.FAILED


async def test_backoff_schedule():
    assert [queue.backoff(n).total_seconds() for n in (1, 2, 3, 4, 5)] == [5, 20, 80, 320, 600]


async def test_requeue_stale(session):
    await queue.enqueue(session, "stuck")
    await session.commit()
    job = await queue.claim(session, "dead-worker")
    assert await queue.requeue_stale(session, timedelta(minutes=10)) == 0
    assert await queue.requeue_stale(session, timedelta(seconds=-1)) == 1
    await session.refresh(job)
    assert job.status == JobStatus.QUEUED and job.locked_by is None


async def test_worker_runs_kickoff(session, user_id):
    project = Project(owner_id=user_id, business_name="Kaapi House", business_type="café")
    session.add(project)
    await session.flush()
    await queue.enqueue(session, "project.kickoff", project_id=project.id)
    await session.commit()

    assert await run_one(SessionLocal, "test") is True
    assert await run_one(SessionLocal, "test") is False

    await session.refresh(project)
    assert project.status == ProjectStatus.RESEARCHING
    evs = await since(session, project.id)
    assert [(e.agent, e.kind) for e in evs] == [("Producer", "status")]


async def test_worker_records_handler_errors(session):
    async def explode(_s, _j):
        raise RuntimeError("handler blew up")

    HANDLERS["test.explode"] = explode
    try:
        job = await queue.enqueue(session, "test.explode", max_attempts=1)
        unknown = await queue.enqueue(session, "test.unknown", max_attempts=1)
        await session.commit()
        await run_one(SessionLocal, "test")
        await run_one(SessionLocal, "test")
    finally:
        del HANDLERS["test.explode"]

    for j, needle in [(job, "handler blew up"), (unknown, "No handler")]:
        fresh = await session.get(Job, j.id, populate_existing=True)
        assert fresh.status == JobStatus.FAILED and needle in fresh.last_error
