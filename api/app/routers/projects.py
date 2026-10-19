import asyncio
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app import events, queue
from app.auth import User
from app.config import Settings, get_settings
from app.db import SessionLocal, get_session
from app.events import emit
from app.models import Artifact, Brief, Project, ProjectStatus
from app.schemas import ArtifactOut, BriefIn, DetailOut, DetailsIn, DetailsOut, DirectionDecision, EventOut, ProjectOut
from app.site.details import find_placeholders
from app.site.images import MAX_PHOTOS, UploadError, delete_upload, save_upload

router = APIRouter(prefix="/projects", tags=["projects"])
# Each revision costs model calls from the shared free quota.
MAX_STYLE_VERSIONS = 5
MAX_BUILDS = 8
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
    project = await session.scalar(
        select(Project)
        .where(Project.id == project_id)
        .with_for_update()
        .execution_options(populate_existing=True)  # re-read under the lock, not the cached copy
    )
    if project.status != ProjectStatus.AWAITING_APPROVAL:
        raise HTTPException(status.HTTP_409_CONFLICT, "There is no direction waiting for approval")

    if body.decision == "approve":
        project.status = ProjectStatus.COPY
        await emit(session, project.id, "Creative director", "status", "Direction approved. The copywriter starts now.")
        await queue.enqueue(session, "agent.copy", project_id=project.id)
    else:
        versions = await session.scalar(
            select(func.count())
            .select_from(Artifact)
            .where(Artifact.project_id == project.id, Artifact.kind == "style")
        )
        if versions >= MAX_STYLE_VERSIONS:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"This demo allows {MAX_STYLE_VERSIONS} versions of the direction. Approve one to continue.",
            )
        note = (body.note or "").strip()
        if len(note) < 5:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Tell the art director what to change")
        project.status = ProjectStatus.DESIGN
        await emit(session, project.id, "Creative director", "status", f"Changes requested: {note}")
        await queue.enqueue(session, "agent.art", {"feedback": note}, project_id=project.id)
    await session.commit()
    await session.refresh(project)
    return project


async def _latest(session: AsyncSession, project_id: uuid.UUID, kind: str) -> Artifact | None:
    return await session.scalar(
        select(Artifact)
        .where(Artifact.project_id == project_id, Artifact.kind == kind)
        .order_by(Artifact.version.desc())
        .limit(1)
    )


@router.get("/{project_id}/details", response_model=DetailsOut)
async def get_details(project_id: uuid.UUID, user: User, session: Session) -> DetailsOut:
    """The [placeholders] in the copy, with any values the owner already gave, plus open research questions."""
    await owned_project(session, project_id, user.id)
    copy = await _latest(session, project_id, "copy")
    saved = await _latest(session, project_id, "details")
    research = await _latest(session, project_id, "research")
    values = saved.content.get("values", {}) if saved else {}
    labels = find_placeholders(copy.content) if copy else []
    return DetailsOut(
        details=[DetailOut(label=label, value=values.get(label, "")) for label in labels],
        questions=research.content.get("open_questions", []) if research else [],
    )


@router.put("/{project_id}/details", response_model=DetailsOut)
async def save_details(project_id: uuid.UUID, body: DetailsIn, user: User, session: Session) -> DetailsOut:
    project = await owned_project(session, project_id, user.id)
    copy = await _latest(session, project_id, "copy")
    if copy is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "The copy is not written yet")
    known = set(find_placeholders(copy.content))
    if unknown := sorted(set(body.values) - known):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown details: {', '.join(unknown)}")
    from app.agents.pipeline import save_artifact

    values = {k: v.strip() for k, v in body.values.items()}
    await save_artifact(session, project, "details", "Owner", {"values": values})
    filled = sum(1 for v in values.values() if v)
    await emit(session, project.id, "Owner", "status", f"Filled in {filled} of {len(known)} details.")
    await session.commit()
    return await get_details(project_id, user, session)


async def _photos(session: AsyncSession, project_id: uuid.UUID) -> list[dict]:
    art = await _latest(session, project_id, "photos")
    return list(art.content.get("items", [])) if art else []


def _photo_out(project_id: uuid.UUID, items: list[dict]) -> list[dict]:
    from app.routers.preview import media_path

    return [{**p, "url": media_path(project_id, p["name"])} for p in items]


@router.get("/{project_id}/photos")
async def list_photos(project_id: uuid.UUID, user: User, session: Session) -> list[dict]:
    await owned_project(session, project_id, user.id)
    return _photo_out(project_id, await _photos(session, project_id))


@router.post("/{project_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_photo(
    project_id: uuid.UUID, user: User, session: Session, file: Annotated[UploadFile, File()]
) -> list[dict]:
    """Add one of the owner's photos. Resized, re-encoded as JPEG and stripped of metadata."""
    from app.agents.pipeline import save_artifact

    project = await owned_project(session, project_id, user.id)
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(f"photos:{project_id}", 0))))
    items = await _photos(session, project_id)
    if len(items) >= MAX_PHOTOS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Up to {MAX_PHOTOS} photos per project")
    data = await file.read(8 * 1024 * 1024 + 1)
    try:
        # Decoding runs in a thread so a large photo cannot stall every other request.
        name, w, h = await asyncio.to_thread(save_upload, project_id, data)
    except UploadError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    alt = (file.filename or "").rsplit(".", 1)[0].replace("_", " ").replace("-", " ")[:100]
    items.append({"name": name, "width": w, "height": h, "alt": alt or project.business_name})
    await save_artifact(session, project, "photos", "Owner", {"items": items})
    await emit(session, project.id, "Owner", "status", f"Added a photo ({len(items)} in total).")
    await session.commit()
    return _photo_out(project_id, items)


@router.delete("/{project_id}/photos/{name}")
async def remove_photo(project_id: uuid.UUID, name: str, user: User, session: Session) -> list[dict]:
    from app.agents.pipeline import save_artifact

    project = await owned_project(session, project_id, user.id)
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(f"photos:{project_id}", 0))))
    items = await _photos(session, project_id)
    keep = [p for p in items if p["name"] != name]
    if len(keep) == len(items):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such photo")
    await save_artifact(session, project, "photos", "Owner", {"items": keep})
    await session.commit()
    delete_upload(project_id, name)
    return _photo_out(project_id, keep)


@router.post("/{project_id}/rebuild", response_model=ProjectOut)
async def rebuild(project_id: uuid.UUID, user: User, session: Session) -> Project:
    """Ask the developer to lay the site out again, e.g. after adding photos."""
    await owned_project(session, project_id, user.id)
    project = await session.scalar(
        select(Project).where(Project.id == project_id).with_for_update().execution_options(populate_existing=True)
    )
    if project.status not in (ProjectStatus.PREVIEW, ProjectStatus.LIVE):
        raise HTTPException(status.HTTP_409_CONFLICT, "The site is still being made")
    builds = await session.scalar(
        select(func.count()).select_from(Artifact).where(Artifact.project_id == project_id, Artifact.kind == "layout")
    )
    if builds >= MAX_BUILDS:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"This demo allows {MAX_BUILDS} rebuilds per project")
    project.status = ProjectStatus.BUILDING
    await emit(session, project.id, "Owner", "status", "Asked the developer to rebuild the pages.")
    await queue.enqueue(session, "agent.build", project_id=project.id)
    await session.commit()
    await session.refresh(project)
    return project
