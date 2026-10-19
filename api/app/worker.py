"""Background worker: `uv run python -m app.worker`.

Handlers are registered by job kind. Each handler gets its own session and the claimed job,
and returns a JSON-able result. Raising marks the job failed (and retried with backoff).
Agent handlers arrive in step 4; for now `project.kickoff` records that the brief was received.
"""

import asyncio
import logging
import os
import socket
import traceback
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import queue
from app.config import get_settings
from app.db import SessionLocal
from app.events import emit
from app.models import Job, Project, ProjectStatus

log = logging.getLogger("studio.worker")

Handler = Callable[[AsyncSession, Job], Awaitable[dict[str, Any] | None]]
HANDLERS: dict[str, Handler] = {}


def handler(kind: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        HANDLERS[kind] = fn
        return fn

    return register


@handler("project.kickoff")
async def kickoff(session: AsyncSession, job: Job) -> dict[str, Any]:
    project = await session.get(Project, job.project_id)
    if project is None:
        return {"skipped": "project deleted"}
    await emit(
        session,
        project.id,
        agent="Producer",
        kind="status",
        message=f"Brief received for {project.business_name}. The researcher is next.",
    )
    project.status = ProjectStatus.RESEARCHING
    await session.commit()
    return {"status": project.status.value}


async def run_one(sessions: async_sessionmaker[AsyncSession], worker_id: str) -> bool:
    """Claim and run a single job. Returns False when the queue is empty."""
    async with sessions() as session:
        job = await queue.claim(session, worker_id)
        if job is None:
            return False
        fn = HANDLERS.get(job.kind)
        try:
            if fn is None:
                raise LookupError(f"No handler for job kind '{job.kind}'")
            result = await fn(session, job)
            await queue.complete(session, job, result)
            log.info("job %s %s succeeded", job.kind, job.id)
        except Exception:
            await session.rollback()
            err = traceback.format_exc()
            # The handler's session may be in a bad state; record the failure on a fresh one.
            async with sessions() as s2:
                fresh = await s2.get(Job, job.id)
                if fresh is not None:
                    await queue.fail(s2, fresh, err)
            log.warning("job %s %s failed (attempt %s)", job.kind, job.id, job.attempts)
        return True


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    settings = get_settings()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    log.info("worker %s started, handlers: %s", worker_id, ", ".join(sorted(HANDLERS)))
    lock_timeout = timedelta(seconds=settings.job_lock_timeout_seconds)
    idle_ticks = 0
    while True:
        if await run_one(SessionLocal, worker_id):
            idle_ticks = 0
            continue
        idle_ticks += 1
        if idle_ticks % 60 == 0:
            async with SessionLocal() as session:
                if n := await queue.requeue_stale(session, lock_timeout):
                    log.warning("requeued %s stale jobs", n)
        await asyncio.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(main())
