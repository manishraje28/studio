"""Revisions: the owner asks for changes in plain words; the Producer plans them and the right
agents carry them out. Every change becomes new artifact versions, so it can be undone, and the
live site only changes when the owner publishes again.
"""

import copy as _copy
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.copywriting import PageCopy, SectionCopy
from app.agents.team import COPY_RULES, GROUND_RULES, ArtDirector, Context, Copywriter, Developer
from app.events import emit
from app.llm import LLMClient
from app.models import Artifact, Job, Project, ProjectStatus

EDITABLE = ("strategy", "style", "copy", "layout")
MAX_PAGES = 8

Op = Literal["edit_copy", "add_section", "remove_section", "add_page", "remove_page", "restyle", "relayout"]


class ChangeStep(BaseModel):
    op: Op
    page: str | None = Field(default=None, description="Page slug; empty string for the home page")
    section_index: int | None = Field(default=None, description="0-based section on that page, if one is meant")
    instruction: str = Field(description="What exactly to change, in the owner's terms")
    title: str | None = Field(default=None, description="For add_page: the page title")


class RevisionPlan(BaseModel):
    summary: str = Field(description="One sentence for the owner: what will change")
    steps: list[ChangeStep] = Field(min_length=1, max_length=8)
    out_of_scope: str | None = Field(
        default=None, description="Anything asked for that the studio cannot do (e.g. online payments), else null"
    )


PLANNER_RULES = """Operations:
- edit_copy: rewrite text. Give page and section_index for one section, or only page for the whole page.
- add_section: new section on a page, after section_index (or at the end if null).
- remove_section: delete one section (page and section_index required).
- add_page: a new page (title required). remove_page: delete a page (never the home page "").
- restyle: change colours, fonts or overall look of the whole site.
- relayout: change how a page is arranged (order of blocks, more photos) without new text.
Use the fewest steps that do exactly what the owner asked. Do not change anything else.
Details like phone numbers, hours and addresses are edited by the owner in the details form; if that is all
they ask for, use edit_copy only when the text itself must change."""


def site_outline(ctx: Context) -> list[dict]:
    return [
        {
            "page": p["slug"],
            "title": p.get("seo_title"),
            "sections": [f"{i}: {s['section']} | {s['heading']}" for i, s in enumerate(p["sections"])],
        }
        for p in ctx.artifacts["copy"]["pages"]
    ]


class Producer:
    name = "Producer"

    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def plan(self, ctx: Context, request: str, page: str | None, section_index: int | None) -> RevisionPlan:
        focus = ""
        if page is not None:
            focus = f"\nThe owner pointed at page '{page}'" + (
                f", section {section_index}." if section_index is not None else "."
            )
        prompt = (
            f"Site outline:\n{json.dumps(site_outline(ctx), ensure_ascii=False, indent=1)}\n\n"
            f"<owner_request>{request}</owner_request>{focus}\n\nPlan the change."
        )
        return await self.llm.complete_json(
            RevisionPlan,
            [{"role": "user", "content": prompt}],
            system=f"You are the Producer. You turn the owner's change request into precise steps.\n"
            f"{PLANNER_RULES}\n{GROUND_RULES}",
            project_id=ctx.project.id,
            agent=self.name,
            temperature=0.2,
        )


async def rewrite_section(
    llm: LLMClient, ctx: Context, page: dict, section: dict | None, instruction: str
) -> SectionCopy:
    """One section, new or rewritten, in the site's voice and under the same copy rules."""
    research = json.dumps(ctx.artifacts["research"], ensure_ascii=False)
    current = (
        f"Current section:\n{json.dumps(section, ensure_ascii=False)}\n" if section else "This is a new section.\n"
    )
    prompt = (
        f"{ctx.brief_block()}\n\n<research>\n{research}\n</research>\n\n"
        f"Page: {page.get('seo_title') or page['slug']}\n{current}"
        f"<owner_request>{instruction}</owner_request>\n\n"
        "Write the section. Change only what the request asks; keep everything else as it was."
    )
    # PageCopy carries the house-style checks (dashes, banned words), so wrap the one section in it.
    result = await llm.complete_json(
        PageCopy,
        [{"role": "user", "content": prompt + "\nReturn a page object with exactly one section."}],
        system=f"You are the Copywriter.\n{GROUND_RULES}\n{COPY_RULES}",
        project_id=ctx.project.id,
        agent=Copywriter.name,
        temperature=0.5,
    )
    return result.sections[0]


def _slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "page"


async def apply_plan(
    session: AsyncSession, llm: LLMClient, project: Project, ctx: Context, plan: RevisionPlan
) -> tuple[dict[str, dict], list[str]]:
    """Run each step. Returns the changed artifacts (kind -> new content) and a log for the owner."""
    strategy = _copy.deepcopy(ctx.artifacts["strategy"])
    site_copy = _copy.deepcopy(ctx.artifacts["copy"])
    changed: dict[str, dict] = {}
    log: list[str] = []
    replan = False

    def page_copy(slug: str | None) -> dict | None:
        return next((p for p in site_copy["pages"] if p["slug"] == (slug or "")), None)

    def page_plan(slug: str) -> dict | None:
        return next((p for p in strategy["pages"] if p["slug"] == slug), None)

    for step in plan.steps:
        if step.op == "edit_copy":
            page = page_copy(step.page)
            if page is None:
                continue
            indexes = (
                [step.section_index]
                if step.section_index is not None and 0 <= step.section_index < len(page["sections"])
                else range(len(page["sections"]))
            )
            for i in indexes:
                await emit(session, project.id, "Copywriter", "progress", f"Rewriting {page['sections'][i]['heading']}")
                await session.commit()
                new = await rewrite_section(llm, ctx, page, page["sections"][i], step.instruction)
                page["sections"][i] = {**new.model_dump(), "section": page["sections"][i]["section"]}
            log.append(f"Rewrote text on {page.get('seo_title') or 'the page'}")
            changed["copy"] = site_copy

        elif step.op == "add_section":
            page = page_copy(step.page)
            if page is None or len(page["sections"]) >= 10:
                continue
            await emit(session, project.id, "Copywriter", "progress", "Writing a new section")
            await session.commit()
            new = await rewrite_section(llm, ctx, page, None, step.instruction)
            at = (
                len(page["sections"])
                if step.section_index is None
                else min(step.section_index + 1, len(page["sections"]))
            )
            page["sections"].insert(at, new.model_dump())
            plan_page = page_plan(page["slug"])
            if plan_page is not None:
                plan_page["sections"].insert(min(at, len(plan_page["sections"])), new.section)
            log.append(f'Added the section "{new.heading}"')
            changed["copy"], changed["strategy"], replan = site_copy, strategy, True

        elif step.op == "remove_section":
            page = page_copy(step.page)
            if page is None or step.section_index is None or not 0 <= step.section_index < len(page["sections"]):
                continue
            if len(page["sections"]) <= 1:
                continue
            gone = page["sections"].pop(step.section_index)
            log.append(f'Removed the section "{gone["heading"]}"')
            changed["copy"], replan = site_copy, True

        elif step.op == "add_page":
            if len(strategy["pages"]) >= MAX_PAGES or not step.title:
                continue
            slug = _slugify(step.title)
            while page_plan(slug) is not None:
                slug += "-2"
            new_plan = {"slug": slug, "title": step.title, "goal": step.instruction, "sections": ["Intro", "Details"]}
            await emit(session, project.id, "Copywriter", "progress", f"Writing the new {step.title} page")
            await session.commit()
            ctx.artifacts["strategy"] = strategy
            written = (await Copywriter(llm).run_page(ctx, {**new_plan, "goal": step.instruction})).model_dump()
            written["slug"] = slug
            new_plan["sections"] = [s["section"] for s in written["sections"]]
            strategy["pages"].append(new_plan)
            site_copy["pages"].append(written)
            log.append(f"Added a new page: {step.title}")
            changed["copy"], changed["strategy"], replan = site_copy, strategy, True

        elif step.op == "remove_page":
            slug = step.page or ""
            if not slug or page_plan(slug) is None:
                continue  # the home page always stays
            strategy["pages"] = [p for p in strategy["pages"] if p["slug"] != slug]
            site_copy["pages"] = [p for p in site_copy["pages"] if p["slug"] != slug]
            log.append(f"Removed the page /{slug}")
            changed["copy"], changed["strategy"], replan = site_copy, strategy, True

        elif step.op == "restyle":
            await emit(session, project.id, "Art director", "progress", "Adjusting the look")
            await session.commit()
            tile = await ArtDirector(llm).run(ctx, step.instruction)
            changed["style"] = tile.model_dump()
            ctx.artifacts["style"] = changed["style"]
            log.append(f"New look: {tile.typography.heading_font} headings, accent {tile.palette.accent}")

        elif step.op == "relayout":
            replan = True
            log.append("Rearranged the layout")

    if replan:
        ctx.artifacts["copy"], ctx.artifacts["strategy"] = site_copy, strategy
        await emit(session, project.id, "Developer", "progress", "Laying the pages out again")
        await session.commit()
        from app.agents.pipeline import photo_pool

        count = len(photo_pool(project, ctx.artifacts, lambda n: n))
        changed["layout"] = (await Developer(llm).plan(ctx, photo_count=count)).model_dump()
    return changed, log


async def current_versions(session: AsyncSession, project_id) -> dict[str, int]:
    rows = await session.execute(
        select(Artifact.kind, func.max(Artifact.version))
        .where(Artifact.project_id == project_id, Artifact.kind.in_(EDITABLE))
        .group_by(Artifact.kind)
    )
    return dict(rows.all())


async def handle_revision(
    session: AsyncSession, job: Job, llm: LLMClient, save_artifact, load_context
) -> dict[str, Any]:
    project = await session.get(Project, job.project_id) if job.project_id else None
    if project is None:
        return {"skipped": "project deleted"}
    request = job.payload["request"]
    ctx = await load_context(session, project)
    before = await current_versions(session, project.id)

    producer = Producer(llm)
    await emit(session, project.id, producer.name, "progress", "Reading your change request")
    await session.commit()
    plan = await producer.plan(ctx, request, job.payload.get("page"), job.payload.get("section_index"))
    await emit(session, project.id, producer.name, "progress", f"Plan: {plan.summary}")
    await session.commit()

    changed, log = await apply_plan(session, llm, project, ctx, plan)
    for kind, content in changed.items():
        await save_artifact(session, project, kind, "Revision", content)
    after = await current_versions(session, project.id)
    record = {
        "request": request,
        "summary": plan.summary,
        "changes": log,
        "out_of_scope": plan.out_of_scope,
        "before": before,
        "after": after,
    }
    await save_artifact(session, project, "revision", producer.name, record)
    project.status = ProjectStatus.PREVIEW
    note = f" Note: {plan.out_of_scope}" if plan.out_of_scope else ""
    await emit(
        session,
        project.id,
        producer.name,
        "artifact",
        ("Done: " + "; ".join(log) + "." if log else "Nothing needed changing.")
        + " Check the preview, then publish when you are happy."
        + note,
        {"kind": "revision"},
    )
    await session.commit()
    return {"changed": sorted(changed)}
