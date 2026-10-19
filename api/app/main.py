from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth import User
from app.config import get_settings
from app.db import SessionLocal
from app.routers import projects

settings = get_settings()

app = FastAPI(title="Studio API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(projects.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    async with SessionLocal() as session:
        await session.execute(text("select 1"))
    return {"status": "ok"}


@app.get("/me", tags=["meta"])
async def me(user: User) -> dict[str, str | None]:
    return {"id": str(user.id), "email": user.email}
