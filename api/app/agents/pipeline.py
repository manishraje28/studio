"""Job handlers that move a project through the studio, one agent at a time.

kickoff -> agent.research -> agent.strategy -> (art director, step 5)
Each handler saves its artifact, writes events for the studio floor, and queues the next step.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import queue
from app.agents.team import Context, Researcher, Strategist
from app.events import emit
from app.llm import get_llm
from app.models import Artifact, Brief, Job, Project, ProjectStatus
from app.registry import handler


async def load_context(session: AsyncSession, project: Project) -> Context:
    brief = await session.get(Brief, project.id)
    latest = (
        select(Artifact.kind, func.max(Artifact.version).label("v"))
        .where(Artifact.project_id == project.id)
        .group_by(Artifact.kind)
        .subquery()
    )
    rows = await session.scalars(
        select(Artifact).join(latest, (Artifact.kind == latest.c.kind) & (Artifact.version == latest.c.v))
    )
    return Context(project, brief.answers if brief else {}, {a.kind: a.content for a in rows})


async def save_artifact(session: AsyncSession, project: Project, kind: str, agent: str, content: dict) -> Artifact:
    version = (
        await session.scalar(
            select(func.coalesce(func.max(Artifact.version), 0)).where(
                Artifact.project_id == project.id, Artifact.kind == kind
            )
        )
    ) + 1
    artifact = Artifact(project_id=project.id, kind=kind, version=version, agent=agent, content=content)
    session.add(artifact)
    await session.flush()
    return artifact


async def _project(session: AsyncSession, job: Job) -> Project | None:
    return await session.get(Project, job.project_id) if job.project_id else None


@handler("project.kickoff")
async def kickoff(session: AsyncSession, job: Job) -> dict[str, Any]:
    project = await _project(session, job)
    if project is None:
        return {"skipped": "project deleted"}
    await emit(
        session,
        project.id,
        "Producer",
        "status",
        f"Brief received for {project.business_name}. Handing it to the researcher.",
    )
    project.status = ProjectStatus.RESEARCHING
    await queue.enqueue(session, "agent.research", project_id=project.id)
    await session.commit()
    return {"next": "agent.research"}


@handler("agent.research")
async def research(session: AsyncSession, job: Job) -> dict[str, Any]:
    project = await _project(session, job)
    if project is None:
        return {"skipped": "project deleted"}
    ctx = await load_context(session, project)
    agent = Researcher(get_llm())

    if project.website_url:
        await emit(session, project.id, agent.name, "progress", f"Reading {project.website_url}")
        await session.commit()
    page, fetch_error = await agent.read_website(ctx)
    if fetch_error:
        await emit(
            session,
            project.id,
            agent.name,
            "progress",
            f"Could not read the website ({fetch_error}). Working from the brief.",
        )
    elif page:
        await emit(
            session,
            project.id,
            agent.name,
            "progress",
            f"Read the website: {len(page.headings)} headings, {len(page.text)} characters of text.",
        )
    await emit(session, project.id, agent.name, "progress", "Writing the research file")
    await session.commit()

    dossier = await agent.run(ctx, page)
    artifact = await save_artifact(session, project, "research", agent.name, dossier.model_dump())
    await emit(
        session,
        project.id,
        agent.name,
        "artifact",
        f"Research file ready: {len(dossier.audiences)} audiences, {len(dossier.facts)} facts, "
        f"{len(dossier.open_questions)} questions for you.",
        {"artifact_id": str(artifact.id), "kind": "research"},
    )
    project.status = ProjectStatus.STRATEGY
    await queue.enqueue(session, "agent.strategy", project_id=project.id)
    await session.commit()
    return {"artifact": str(artifact.id)}


@handler("agent.strategy")
async def strategy(session: AsyncSession, job: Job) -> dict[str, Any]:
    project = await _project(session, job)
    if project is None:
        return {"skipped": "project deleted"}
    ctx = await load_context(session, project)
    if "research" not in ctx.artifacts:
        raise RuntimeError("strategy needs the research file first")
    agent = Strategist(get_llm())
    await emit(session, project.id, agent.name, "progress", "Planning pages and the main call to action")
    await session.commit()

    plan = await agent.run(ctx)
    artifact = await save_artifact(session, project, "strategy", agent.name, plan.model_dump())
    pages = ", ".join(p.title for p in plan.pages)
    await emit(
        session,
        project.id,
        agent.name,
        "artifact",
        f"Sitemap ready: {pages}. Main action: {plan.primary_action.label}.",
        {"artifact_id": str(artifact.id), "kind": "strategy"},
    )
    project.status = ProjectStatus.DESIGN
    await emit(session, project.id, "Producer", "status", "Strategy done. The art director starts next.")
    await session.commit()
    return {"artifact": str(artifact.id)}
