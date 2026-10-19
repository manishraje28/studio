"""Create tables, and on Supabase also enable row level security.

Run with `uv run python -m app.migrate`. Safe to run repeatedly.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.db import Base, engine

# The API connects with the service role and enforces ownership itself. RLS is a second wall:
# if the anon key ever reaches these tables directly, users only see their own rows,
# and jobs are never exposed.
RLS_STATEMENTS = [
    "alter table projects enable row level security",
    "alter table briefs enable row level security",
    "alter table agent_events enable row level security",
    "alter table jobs enable row level security",
    "alter table llm_calls enable row level security",
    "alter table artifacts enable row level security",
    "drop policy if exists projects_owner on projects",
    "create policy projects_owner on projects for select using (owner_id = auth.uid())",
    "drop policy if exists briefs_owner on briefs",
    "create policy briefs_owner on briefs for select using "
    "(exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid()))",
    "drop policy if exists artifacts_owner on artifacts",
    "create policy artifacts_owner on artifacts for select using "
    "(exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid()))",
    "drop policy if exists events_owner on agent_events",
    "create policy events_owner on agent_events for select using "
    "(exists (select 1 from projects p where p.id = project_id and p.owner_id = auth.uid()))",
]


async def migrate(db: AsyncEngine = engine) -> None:
    async with db.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # create_all never changes an existing enum type; add values introduced after the first deploy.
        for value in [s.value for s in models.ProjectStatus]:
            await conn.execute(text(f"alter type project_status add value if not exists '{value}'"))
        has_auth = await conn.scalar(text("select exists (select 1 from pg_namespace where nspname = 'auth')"))
        if has_auth:
            for stmt in RLS_STATEMENTS:
                await conn.execute(text(stmt))


if __name__ == "__main__":
    asyncio.run(migrate())
    print("Database is up to date.")
