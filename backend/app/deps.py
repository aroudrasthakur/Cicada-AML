"""FastAPI dependencies (auth, etc.)."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWTError
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from app.config import settings

_bearer = HTTPBearer(auto_error=False)

_jwks_client: PyJWKClient | None = None


def _jwks_client_singleton() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        base = (settings.supabase_url or "").strip().rstrip("/")
        jwks_url = f"{base}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def _decode_payload_hs256(token: str) -> dict:
    secret = (settings.supabase_jwt_secret or "").strip()
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=settings.supabase_jwt_audience,
            leeway=120,
        )
    except jwt.InvalidAudienceError:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
            leeway=120,
        )


def _decode_payload_jwks(token: str, alg: str) -> dict:
    signing_key = _jwks_client_singleton().get_signing_key_from_jwt(token)
    if alg not in ("ES256", "RS256"):
        alg = "ES256"
    try:
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience=settings.supabase_jwt_audience,
            leeway=120,
        )
    except jwt.InvalidAudienceError:
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            options={"verify_aud": False},
            leeway=120,
        )


def _decode_supabase_access_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except PyJWTError as e:
        raise HTTPException(401, "Invalid or expired token") from e

    alg = header.get("alg") or ""

    if alg == "HS256":
        if not (settings.supabase_jwt_secret or "").strip():
            raise HTTPException(
                503,
                "HS256 token received but SUPABASE_JWT_SECRET is not set in the API environment.",
            )
        try:
            return _decode_payload_hs256(token)
        except PyJWTError:
            raise HTTPException(401, "Invalid or expired token") from None

    if not (settings.supabase_url or "").strip():
        raise HTTPException(
            503,
            "Authentication is not configured: set SUPABASE_URL in the API environment "
            "(needed for JWKS verification of ES256/RS256 tokens).",
        )
    try:
        return _decode_payload_jwks(token, alg)
    except (PyJWKClientConnectionError, PyJWKClientError) as e:
        raise HTTPException(
            503,
            "Could not reach Supabase JWKS endpoint; check SUPABASE_URL and network.",
        ) from e
    except PyJWTError:
        raise HTTPException(401, "Invalid or expired token") from None


async def get_current_user_id(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Validate Supabase access token (Bearer); return JWT ``sub`` (user UUID)."""
    if not (settings.supabase_url or "").strip() and not (
        settings.supabase_jwt_secret or ""
    ).strip():
        raise HTTPException(
            503,
            "Authentication is not configured: set SUPABASE_URL and/or SUPABASE_JWT_SECRET "
            "in the API environment.",
        )
    if creds is None or not creds.credentials:
        raise HTTPException(401, "Not authenticated")

    payload = _decode_supabase_access_token(creds.credentials)
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(401, "Invalid token payload")
    return sub
