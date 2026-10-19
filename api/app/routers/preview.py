"""Client site previews, loadable in an iframe without an auth header.

Links carry an HMAC of the project id, so only people the owner shares the link with can open
them. Pages are rendered on request from the latest artifacts and served with a strict CSP:
no scripts, no forms, styles and fonts only.
"""

import hashlib
import hmac
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.pipeline import load_context, render_project
from app.auth import User
from app.config import get_settings
from app.db import get_session
from app.models import Project
from app.site.images import upload_path

router = APIRouter(tags=["preview"])
Session = Annotated[AsyncSession, Depends(get_session)]


def preview_token(project_id: uuid.UUID) -> str:
    settings = get_settings()
    secret = settings.preview_secret or settings.supabase_jwt_secret
    if not secret:
        raise HTTPException(500, "Set PREVIEW_SECRET to enable previews")
    return hmac.new(secret.encode(), f"preview:{project_id}".encode(), hashlib.sha256).hexdigest()[:32]


def preview_path(project_id: uuid.UUID, slug: str) -> str:
    return f"/preview/{project_id}/{slug}?t={preview_token(project_id)}"


def media_path(project_id: uuid.UUID, name: str) -> str:
    return f"/media/{project_id}/{name}?t={preview_token(project_id)}"


def csp() -> str:
    ancestors = " ".join(get_settings().cors_origins)
    return (
        "default-src 'none'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' https: data:; base-uri 'none'; form-action 'none'; "
        f"frame-ancestors 'self' {ancestors}"
    )


@router.get("/projects/{project_id}/preview")
async def preview_link(project_id: uuid.UUID, user: User, session: Session) -> dict[str, str]:
    from app.routers.projects import owned_project

    await owned_project(session, project_id, user.id)
    return {"path": preview_path(project_id, "")}


@router.get("/preview/{project_id}/", response_class=HTMLResponse)
async def preview_home(project_id: uuid.UUID, session: Session, t: Annotated[str, Query()] = ""):
    return await preview_page(project_id, "", session, t)


@router.get("/preview/{project_id}/{slug:path}", response_class=HTMLResponse)
async def preview_page(project_id: uuid.UUID, slug: str, session: Session, t: Annotated[str, Query()] = ""):
    if not hmac.compare_digest(t, preview_token(project_id)):
        raise HTTPException(404, "Not found")
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Not found")
    ctx = await load_context(session, project)
    if not {"strategy", "style", "copy", "layout"} <= ctx.artifacts.keys():
        raise HTTPException(404, "The preview is not ready yet")
    pages = render_project(
        project, ctx.artifacts, lambda s: preview_path(project_id, s), lambda name: media_path(project_id, name)
    )
    html = pages.get(slug.strip("/"))
    if html is None:
        raise HTTPException(404, "No such page")
    return HTMLResponse(
        html,
        headers={
            "Content-Security-Policy": csp(),
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "no-store",
        },
    )


@router.get("/media/{project_id}/{name}")
async def media(project_id: uuid.UUID, name: str, t: Annotated[str, Query()] = ""):
    """The owner's uploaded photos, readable with the same signed token as the preview."""
    if not hmac.compare_digest(t, preview_token(project_id)):
        raise HTTPException(404, "Not found")
    path = upload_path(project_id, name)
    if path is None:
        raise HTTPException(404, "Not found")
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=86400"},
    )
