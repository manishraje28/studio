from fastapi import APIRouter

from app.auth import User
from app.llm import get_llm

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/status")
async def status(_user: User) -> dict:
    """Which providers are active (never the keys) and how much of today's budget is used."""
    llm = get_llm()
    return {
        "providers": [{"name": p.name, "model": p.model} for p in llm.providers],
        "calls_today": await llm.calls_today(),
        "daily_limit": llm.daily_call_limit,
    }
