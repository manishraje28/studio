import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str | None


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"{url.rstrip('/')}/auth/v1/.well-known/jwks.json", cache_keys=True)


def decode_token(token: str, settings: Settings) -> dict:
    """Verify a Supabase access token. Prefers the project's JWKS; falls back to the HS256 secret."""
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            raise jwt.InvalidTokenError("HS256 tokens are not accepted: no shared secret configured")
        key = settings.supabase_jwt_secret
    elif settings.supabase_url:
        key = _jwks_client(settings.supabase_url).get_signing_key_from_jwt(token).key
    else:
        raise jwt.InvalidTokenError(f"Cannot verify {alg} token: SUPABASE_URL is not set")
    return jwt.decode(
        token,
        key,
        algorithms=["HS256", "RS256", "ES256"],
        audience=settings.jwt_audience,
        options={"require": ["exp", "sub"]},
    )


async def current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CurrentUser:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    try:
        claims = decode_token(creds.credentials, settings)
        return CurrentUser(id=uuid.UUID(claims["sub"]), email=claims.get("email"))
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc


User = Annotated[CurrentUser, Depends(current_user)]
