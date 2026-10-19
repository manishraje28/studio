"""A small job queue on Postgres.

Workers claim jobs with `FOR UPDATE SKIP LOCKED`, so any number of workers can poll the same
table without double-processing. Failed jobs retry with exponential backoff until max_attempts.
Jobs whose worker died mid-run are put back on the queue after the lock timeout.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Job, JobStatus


async def enqueue(
    session: AsyncSession,
    kind: str,
    payload: dict[str, Any] | None = None,
    *,
    project_id: uuid.UUID | None = None,
    delay: timedelta | None = None,
    max_attempts: int = 3,
) -> Job:
    job = Job(
        kind=kind,
        payload=payload or {},
        project_id=project_id,
        max_attempts=max_attempts,
        run_at=datetime.now(UTC) + (delay or timedelta()),
    )
    session.add(job)
    await session.flush()
    return job


async def claim(session: AsyncSession, worker_id: str) -> Job | None:
    """Lock and return the next due job, or None. Commits the claim immediately."""
    now = datetime.now(UTC)
    stmt = (
        select(Job)
        .where(and_(Job.status == JobStatus.QUEUED, Job.run_at <= now))
        .order_by(Job.run_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = await session.scalar(stmt)
    if job is None:
        await session.rollback()
        return None
    job.status = JobStatus.RUNNING
    job.attempts += 1
    job.locked_at = now
    job.locked_by = worker_id
    await session.commit()
    return job


async def complete(session: AsyncSession, job: Job, result: dict[str, Any] | None = None) -> None:
    job.status = JobStatus.SUCCEEDED
    job.result = result
    job.locked_at = None
    job.locked_by = None
    await session.commit()


def backoff(attempt: int) -> timedelta:
    """5s, 20s, 80s, ... capped at 10 minutes."""
    return timedelta(seconds=min(5 * 4 ** (attempt - 1), 600))


async def fail(session: AsyncSession, job: Job, error: str) -> None:
    job.last_error = error[:4000]
    job.locked_at = None
    job.locked_by = None
    if job.attempts >= job.max_attempts:
        job.status = JobStatus.FAILED
    else:
        job.status = JobStatus.QUEUED
        job.run_at = datetime.now(UTC) + backoff(job.attempts)
    await session.commit()


async def requeue_stale(session: AsyncSession, lock_timeout: timedelta) -> int:
    """Return jobs stuck in RUNNING (their worker crashed) to the queue."""
    cutoff = datetime.now(UTC) - lock_timeout
    res = await session.execute(
        update(Job)
        .where(and_(Job.status == JobStatus.RUNNING, Job.locked_at < cutoff))
        .values(status=JobStatus.QUEUED, locked_at=None, locked_by=None, run_at=datetime.now(UTC))
    )
    await session.commit()
    return res.rowcount or 0
