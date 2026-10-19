import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentEvent


async def emit(
    session: AsyncSession,
    project_id: uuid.UUID,
    agent: str,
    kind: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> AgentEvent:
    event = AgentEvent(project_id=project_id, agent=agent, kind=kind, message=message, data=data or {})
    session.add(event)
    await session.flush()
    return event


async def since(session: AsyncSession, project_id: uuid.UUID, after_id: int = 0, limit: int = 200):
    rows = await session.scalars(
        select(AgentEvent)
        .where(AgentEvent.project_id == project_id, AgentEvent.id > after_id)
        .order_by(AgentEvent.id)
        .limit(limit)
    )
    return list(rows)
