import asyncio
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app import events, queue
from app.auth import User
from app.config import Settings, get_settings
from app.db import SessionLocal, get_session
from app.events import emit
from app.models import Artifact, Brief, Project, ProjectStatus
from app.schemas import ArtifactOut, BriefIn, DirectionDecision, EventOut, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])
Session = Annotated[AsyncSession, Depends(get_session)]


async def owned_project(session: AsyncSession, project_id: uuid.UUID, owner_id: uuid.UUID) -> Project:
    project = await session.get(Project, project_id)
    # 404 rather than 403, so ids of other people's projects are not confirmed to exist.
    if project is None or project.owner_id != owner_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: BriefIn, user: User, session: Session, settings: Annotated[Settings, Depends(get_settings)]
) -> Project:
    # Serialize project creation per user so parallel requests cannot all pass the limit check.
    # The lock is released when this transaction commits or rolls back.
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(str(user.id), 0))))
    start_of_day = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today = await session.scalar(
        select(func.count()).select_from(Project).where(Project.owner_id == user.id, Project.created_at >= start_of_day)
    )
    if (today or 0) >= settings.daily_project_limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"The demo allows {settings.daily_project_limit} new projects per day. Try again tomorrow.",
        )

    project = Project(
        owner_id=user.id,
        business_name=body.business_name.strip(),
        business_type=body.business_type.strip(),
        city=body.city,
        website_url=str(body.website_url) if body.website_url else None,
        brief=Brief(answers=body.answers),
    )
    session.add(project)
    await session.flush()
    await queue.enqueue(session, "project.kickoff", project_id=project.id)
    await session.commit()
    await session.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(user: User, session: Session) -> list[Project]:
    rows = await session.scalars(select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc()))
    return list(rows)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, user: User, session: Session) -> Project:
    return await owned_project(session, project_id, user.id)


@router.get("/{project_id}/events", response_model=list[EventOut])
async def list_events(project_id: uuid.UUID, user: User, session: Session, after: Annotated[int, Query(ge=0)] = 0):
    await owned_project(session, project_id, user.id)
    return await events.since(session, project_id, after)


@router.get("/{project_id}/events/stream")
async def stream_events(project_id: uuid.UUID, user: User, request: Request, after: Annotated[int, Query(ge=0)] = 0):
    """Server-sent events for the live studio floor. Polls the table once a second."""
    async with SessionLocal() as session:
        await owned_project(session, project_id, user.id)

    async def gen():
        last = after
        while not await request.is_disconnected():
            async with SessionLocal() as session:
                batch = await events.since(session, project_id, last)
            for ev in batch:
                last = ev.id
                yield {"id": str(ev.id), "event": ev.kind, "data": EventOut.model_validate(ev).model_dump_json()}
            await asyncio.sleep(1)

    return EventSourceResponse(gen(), ping=15)


@router.get("/{project_id}/artifacts", response_model=list[ArtifactOut])
async def list_artifacts(project_id: uuid.UUID, user: User, session: Session) -> list[Artifact]:
    """Every version of every deliverable, newest first."""
    await owned_project(session, project_id, user.id)
    rows = await session.scalars(
        select(Artifact).where(Artifact.project_id == project_id).order_by(Artifact.kind, Artifact.version.desc())
    )
    return list(rows)


@router.post("/{project_id}/direction", response_model=ProjectOut)
async def decide_direction(project_id: uuid.UUID, body: DirectionDecision, user: User, session: Session) -> Project:
    """The approval gate after art direction: approve to start the copy, or send notes back."""
    await owned_project(session, project_id, user.id)
    # Lock the row so a double click cannot queue the next step twice.
    project = await session.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if project.status != ProjectStatus.AWAITING_APPROVAL:
        raise HTTPException(status.HTTP_409_CONFLICT, "There is no direction waiting for approval")

    if body.decision == "approve":
        project.status = ProjectStatus.COPY
        await emit(session, project.id, "Creative director", "status", "Direction approved. The copywriter starts now.")
        await queue.enqueue(session, "agent.copy", project_id=project.id)
    else:
        note = (body.note or "").strip()
        if len(note) < 5:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Tell the art director what to change")
        project.status = ProjectStatus.DESIGN
        await emit(session, project.id, "Creative director", "status", f"Changes requested: {note}")
        await queue.enqueue(session, "agent.art", {"feedback": note}, project_id=project.id)
    await session.commit()
    await session.refresh(project)
    return project
