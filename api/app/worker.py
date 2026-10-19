"""Background worker: `uv run python -m app.worker`.

Handlers are registered by job kind. Each handler gets its own session and the claimed job,
and returns a JSON-able result. Raising marks the job failed (and retried with backoff).
Handlers live in app/agents/pipeline.py and register themselves in app/registry.py.
"""

import asyncio
import logging
import os
import socket
import traceback
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import queue
from app.agents import pipeline  # noqa: F401  (registers the agent job handlers)
from app.config import get_settings
from app.db import SessionLocal
from app.events import emit
from app.models import Job, JobStatus, Project, ProjectStatus
from app.registry import HANDLERS

log = logging.getLogger("studio.worker")


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
                    if fresh.status == JobStatus.FAILED and fresh.project_id:
                        project = await s2.get(Project, fresh.project_id)
                        if project is not None:
                            project.status = ProjectStatus.FAILED
                            await emit(
                                s2,
                                project.id,
                                "Producer",
                                "error",
                                f"The {fresh.kind.removeprefix('agent.')} step failed after {fresh.attempts} attempts "
                                "and has stopped.",
                                {"job": fresh.kind},
                            )
                            await s2.commit()
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
