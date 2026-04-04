"""FastAPI dependencies (auth, etc.)."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer(auto_error=False)


async def get_current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Validate Supabase access token (Bearer); return JWT ``sub`` (user UUID)."""
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            503,
            "Authentication is not configured: set SUPABASE_JWT_SECRET in the API environment.",
        )
    if creds is None or not creds.credentials:
        raise HTTPException(401, "Not authenticated")
    secret = (settings.supabase_jwt_secret or "").strip()
    try:
        payload = jwt.decode(
            creds.credentials,
            secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,
            leeway=120,
        )
    except jwt.InvalidAudienceError:
        # Some project / token shapes omit or alter ``aud``; signature + exp still verified.
        try:
            payload = jwt.decode(
                creds.credentials,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
                leeway=120,
            )
        except jwt.PyJWTError:
            raise HTTPException(
                401,
                "Invalid or expired token",
            ) from None
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token") from None
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(401, "Invalid token payload")
    return sub
