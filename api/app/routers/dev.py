"""Development-only sign-in, so the app can run before a Supabase project exists.

Mounted only when ENV=development. Issues a short-lived HS256 token signed with
SUPABASE_JWT_SECRET for a stable user id derived from the email.
"""

import time
import uuid

import jwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.config import get_settings

router = APIRouter(prefix="/dev", tags=["dev"])
DEV_NAMESPACE = uuid.UUID("5f1c9d1e-7a3b-4c2a-9d4e-111111111111")


class DevLogin(BaseModel):
    email: EmailStr = "dev@example.com"


@router.post("/token")
async def dev_token(body: DevLogin) -> dict[str, str]:
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(500, "Set SUPABASE_JWT_SECRET to use dev sign-in")
    user_id = uuid.uuid5(DEV_NAMESPACE, body.email.lower())
    now = int(time.time())
    claims = {"sub": str(user_id), "email": body.email, "aud": settings.jwt_audience, "iat": now, "exp": now + 8 * 3600}
    return {
        "access_token": jwt.encode(claims, settings.supabase_jwt_secret, algorithm="HS256"),
        "user_id": str(user_id),
    }
