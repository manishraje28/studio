"""Job handlers that move a project through the studio, one agent at a time.

kickoff -> agent.research -> agent.strategy -> (art director, step 5)
Each handler saves its artifact, writes events for the studio floor, and queues the next step.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import queue
from app.agents.team import ArtDirector, Context, Copywriter, Critic, Developer, PhotoScout, Researcher, Strategist
from app.events import emit
from app.llm import get_llm
from app.models import Artifact, Brief, Job, Project, ProjectStatus
from app.registry import handler
from app.site import qa
from app.site.details import fill
from app.site.images import search_stock
from app.site.render import render_site


async def load_context(session: AsyncSession, project: Project) -> Context:
    brief = await session.get(Brief, project.id)
    latest = (
        select(Artifact.kind, func.max(Artifact.version).label("v"))
        .where(Artifact.project_id == project.id)
        .group_by(Artifact.kind)
        .subquery()
    )
    rows = await session.scalars(
        select(Artifact)
        .join(latest, (Artifact.kind == latest.c.kind) & (Artifact.version == latest.c.v))
        .where(Artifact.project_id == project.id)  # the subquery is scoped, the outer query must be too
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
    await queue.enqueue(session, "agent.art", project_id=project.id)
    await session.commit()
    return {"artifact": str(artifact.id)}


@handler("agent.art")
async def art_direction(session: AsyncSession, job: Job) -> dict[str, Any]:
    project = await _project(session, job)
    if project is None:
        return {"skipped": "project deleted"}
    ctx = await load_context(session, project)
    feedback = job.payload.get("feedback")
    agent = ArtDirector(get_llm())
    await emit(
        session,
        project.id,
        agent.name,
        "progress",
        "Revising the direction with your notes" if feedback else "Choosing colours, type and the signature idea",
    )
    await session.commit()

    tile = await agent.run(ctx, feedback)
    artifact = await save_artifact(session, project, "style", agent.name, tile.model_dump())
    ideas = "; ".join(i.name for i in tile.signature_ideas)
    await emit(
        session,
        project.id,
        agent.name,
        "artifact",
        f"Style tile v{artifact.version} ready. {tile.typography.heading_font} with {tile.typography.body_font}. "
        f"Signature: {ideas}.",
        {"artifact_id": str(artifact.id), "kind": "style"},
    )
    project.status = ProjectStatus.AWAITING_APPROVAL
    await emit(
        session,
        project.id,
        "Producer",
        "status",
        "The visual direction needs your approval before anything is written or built.",
    )
    await session.commit()
    return {"artifact": str(artifact.id)}


@handler("agent.copy")
async def copywriting(session: AsyncSession, job: Job) -> dict[str, Any]:
    project = await _project(session, job)
    if project is None:
        return {"skipped": "project deleted"}
    ctx = await load_context(session, project)
    agent = Copywriter(get_llm())
    pages = ctx.artifacts["strategy"]["pages"]
    # One call per page keeps prompts small enough for free-tier models and shows progress.
    # Finished pages are saved on the job as we go, so a retry resumes instead of starting over.
    done: dict[str, dict] = dict(job.payload.get("pages_done", {}))
    for i, page in enumerate(pages, 1):
        if page["slug"] in done:
            continue
        name = "the home page" if not page["slug"] else page["title"]
        await emit(session, project.id, agent.name, "progress", f"Writing {name} ({i} of {len(pages)})")
        await session.commit()
        written_page = (await agent.run_page(ctx, page)).model_dump()
        written_page["slug"] = page["slug"]  # trust the plan, not the model's echo of it
        done[page["slug"]] = written_page
        # Assign a new dict: SQLAlchemy only saves JSON columns when the value it holds changes.
        job.payload = {**job.payload, "pages_done": dict(done)}
        await session.commit()
    written = [done[p["slug"]] for p in pages]

    artifact = await save_artifact(session, project, "copy", agent.name, {"pages": written})
    words = sum(len(f"{s['heading']} {s['body']}".split()) for p in written for s in p["sections"])
    placeholders = sum(f"{s['heading']} {s['body']}".count("[") for p in written for s in p["sections"])
    await emit(
        session,
        project.id,
        agent.name,
        "artifact",
        f"Copy ready for {len(written)} pages, about {words} words."
        + (f" {placeholders} details are marked [like this] for you to fill in." if placeholders else ""),
        {"artifact_id": str(artifact.id), "kind": "copy"},
    )
    project.status = ProjectStatus.BUILDING
    await emit(session, project.id, "Producer", "status", "Copy done. The developer starts next.")
    await queue.enqueue(session, "agent.build", project_id=project.id)
    await session.commit()
    return {"artifact": str(artifact.id)}


@handler("agent.build")
async def build(session: AsyncSession, job: Job) -> dict[str, Any]:
    project = await _project(session, job)
    if project is None:
        return {"skipped": "project deleted"}
    ctx = await load_context(session, project)
    if not ctx.artifacts.get("stock", {}).get("photos"):
        scout = PhotoScout(get_llm())
        await emit(session, project.id, scout.name, "progress", "Looking for free photos of the space and the work")
        await session.commit()
        queries = (await scout.queries(ctx)).queries
        found = await search_stock(queries)
        ctx.artifacts["stock"] = {"queries": queries, "photos": [p.to_dict() for p in found]}
        await save_artifact(session, project, "stock", scout.name, ctx.artifacts["stock"])
        await emit(
            session,
            project.id,
            scout.name,
            "progress",
            f"Found {len(found)} free photos (credited in the footer). Your own uploads always come first.",
        )
        await session.commit()

    agent = Developer(get_llm())
    await emit(session, project.id, agent.name, "progress", "Choosing a layout for every section")
    await session.commit()

    plan = await agent.plan(ctx, photo_count=len(photo_pool(project, ctx.artifacts, lambda n: n)))
    # Render once now so a broken plan fails here, inside the retrying job, not in the preview.
    pages = render_project(project, {**ctx.artifacts, "layout": plan.model_dump()}, lambda slug: f"/{slug}")
    artifact = await save_artifact(session, project, "layout", agent.name, plan.model_dump())
    size = sum(len(html) for html in pages.values()) // 1024
    await emit(
        session,
        project.id,
        agent.name,
        "artifact",
        f"Built {len(pages)} pages ({size} KB). Sending them to the QA critic.",
        {"artifact_id": str(artifact.id), "kind": "layout"},
    )
    project.status = ProjectStatus.QA
    await queue.enqueue(session, "agent.qa", project_id=project.id)
    await session.commit()
    return {"artifact": str(artifact.id), "pages": len(pages)}


def photo_pool(project: Project, artifacts: dict[str, dict], media_url) -> list[dict]:
    """Owner photos first (newest upload last), then credited stock photos."""
    own = [
        {
            "url": media_url(p["name"]),
            "alt": p.get("alt") or project.business_name,
            "credit": None,
            "width": p.get("width", 0),
            "height": p.get("height", 0),
        }
        for p in artifacts.get("photos", {}).get("items", [])
    ]
    return own + artifacts.get("stock", {}).get("photos", [])


def render_project(
    project: Project, artifacts: dict[str, dict], url_for, media_url=lambda name: name
) -> dict[str, str]:
    values = artifacts.get("details", {}).get("values", {})
    return render_site(
        business_name=project.business_name,
        business_type=project.business_type,
        city=project.city,
        strategy=artifacts["strategy"],
        style=artifacts["style"],
        copy=fill(artifacts["copy"], values),
        layout=artifacts["layout"],
        url_for=url_for,
        photos=photo_pool(project, artifacts, media_url),
        details=values,
    )


@handler("agent.qa")
async def quality_check(session: AsyncSession, job: Job) -> dict[str, Any]:
    project = await _project(session, job)
    if project is None:
        return {"skipped": "project deleted"}
    ctx = await load_context(session, project)
    critic = Critic(get_llm())
    await emit(session, project.id, critic.name, "progress", "Checking links, headings, search titles and mobile setup")
    await session.commit()

    pages = render_project(project, ctx.artifacts, lambda slug: f"/{slug}")
    findings = qa.check_site(pages, lambda slug: f"/{slug}")
    site_score = qa.score(findings)
    await emit(session, project.id, critic.name, "progress", "Reading the copy for anything generic")
    await session.commit()
    review = await critic.review(ctx)

    report = {"score": site_score, "findings": qa.as_dicts(findings), "review": review.model_dump()}
    artifact = await save_artifact(session, project, "qa", critic.name, report)
    fails = sum(f.severity == "fail" for f in findings)
    await emit(
        session,
        project.id,
        critic.name,
        "artifact",
        f"Site checks scored {site_score}/100 with {fails} failures. Copy specificity {review.specificity}/10, "
        f"{len(review.generic_lines)} lines to sharpen.",
        {"artifact_id": str(artifact.id), "kind": "qa"},
    )
    project.status = ProjectStatus.PREVIEW
    await emit(session, project.id, "Producer", "status", "Your preview is ready to review.")
    await session.commit()
    return {"score": site_score}
