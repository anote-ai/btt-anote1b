"""
Anote-aligned auth for the leaderboard API.

OpenAnote uses jwt_or_session_token_required on the Flask side. This service:
- Accepts the same Bearer token the SPA puts on requests (localStorage accessToken / sessionToken),
  or optional HttpOnly cookies (see ANOTE_AUTH_COOKIE_NAMES).
- Validates JWTs with ANOTE_JWT_SECRET / JWT_SECRET_KEY (same secret as Flask-JWT-Extended).
- Optionally validates opaque session tokens via ANOTE_TOKEN_INTROSPECT_URL (POST JSON).

Env:
- LEADERBOARD_AUTH_MODE: "off" | "jwt"  (default off; tests keep this off)
- ANOTE_JWT_SECRET or JWT_SECRET_KEY
- ANOTE_JWT_ALGORITHMS: comma list, default HS256,RS256
- ANOTE_JWT_AUDIENCE, ANOTE_JWT_ISSUER: optional
- ANOTE_AUTH_COOKIE_NAMES: e.g. "access_token_cookie" (comma-separated)
- ANOTE_TOKEN_POST_URL + ANOTE_INTROSPECT_TOKEN_FIELD: forward token to Anote (see resolve_user)
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import jwt
import requests
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class AuthUser(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sub: Optional[str] = None
    email: Optional[str] = None


def auth_mode() -> str:
    return (os.getenv("LEADERBOARD_AUTH_MODE") or "off").strip().lower()


def _jwt_secret() -> Optional[str]:
    return (os.getenv("ANOTE_JWT_SECRET") or os.getenv("JWT_SECRET_KEY") or "").strip() or None


def _jwt_algorithms() -> list:
    raw = (os.getenv("ANOTE_JWT_ALGORITHMS") or "HS256").strip()
    return [a.strip() for a in raw.split(",") if a.strip()]


def _cookie_value(cookie_header: str, name: str) -> Optional[str]:
    if not cookie_header or not name:
        return None
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith(name + "="):
            return part.split("=", 1)[1].strip()
    return None


def extract_raw_token(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        t = auth[7:].strip()
        if t:
            return t
    cookie_header = request.headers.get("cookie") or ""
    names_raw = os.getenv("ANOTE_AUTH_COOKIE_NAMES", "").strip()
    if names_raw:
        for name in [x.strip() for x in names_raw.split(",") if x.strip()]:
            val = _cookie_value(cookie_header, name)
            if val:
                return val
    return None


def _decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    secret = _jwt_secret()
    if not secret:
        return None
    audience = (os.getenv("ANOTE_JWT_AUDIENCE") or "").strip() or None
    issuer = (os.getenv("ANOTE_JWT_ISSUER") or "").strip() or None
    algorithms = _jwt_algorithms()
    decode_kw: Dict[str, Any] = {
        "algorithms": algorithms,
        "options": {"verify_aud": bool(audience)},
    }
    if audience:
        decode_kw["audience"] = audience
    if issuer:
        decode_kw["issuer"] = issuer
    try:
        return jwt.decode(token, secret, **decode_kw)
    except jwt.PyJWTError:
        return None


def _introspect_remote(token: str) -> Optional[Dict[str, Any]]:
    """POST token to Anote (or a shim) when JWT verification is not used for session tokens."""
    url = (os.getenv("ANOTE_TOKEN_INTROSPECT_URL") or "").strip()
    if not url:
        return None
    field = (os.getenv("ANOTE_INTROSPECT_TOKEN_FIELD") or "token").strip()
    timeout = float(os.getenv("ANOTE_INTROSPECT_TIMEOUT", "5"))
    headers = {"Content-Type": "application/json"}
    api_key = (os.getenv("ANOTE_INTROSPECT_API_KEY") or "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        r = requests.post(url, json={field: token}, headers=headers, timeout=timeout)
        if r.status_code != 200:
            logger.debug("Introspect HTTP %s", r.status_code)
            return None
        data = r.json()
        if isinstance(data, dict) and data.get("valid") is False:
            return None
        if isinstance(data, dict) and "user" in data and isinstance(data["user"], dict):
            return data["user"]
        if isinstance(data, dict):
            return data
    except (requests.RequestException, ValueError) as e:
        logger.debug("Introspect failed: %s", e)
    return None


def claims_to_user(claims: Dict[str, Any]) -> AuthUser:
    sub = claims.get("sub") or claims.get("identity") or claims.get("user_id")
    if sub is not None:
        sub = str(sub)
    email = claims.get("email")
    if email is not None:
        email = str(email)
    return AuthUser(sub=sub, email=email)


def resolve_user(request: Request) -> Optional[AuthUser]:
    token = extract_raw_token(request)
    if not token:
        return None
    jwt_claims = _decode_jwt(token)
    if jwt_claims:
        return claims_to_user(jwt_claims)
    intro = _introspect_remote(token)
    if intro:
        return claims_to_user(intro)
    return None


def require_write_user(request: Request) -> Optional[AuthUser]:
    """Use as Depends(...). When LEADERBOARD_AUTH_MODE=jwt, requires a valid user."""
    if auth_mode() != "jwt":
        return None
    user = resolve_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not (user.sub or user.email):
        raise HTTPException(status_code=401, detail="Invalid token (missing identity)")
    return user


def log_auth_config() -> None:
    mode = auth_mode()
    has_secret = bool(_jwt_secret())
    has_intro = bool((os.getenv("ANOTE_TOKEN_INTROSPECT_URL") or "").strip())
    cookies = (os.getenv("ANOTE_AUTH_COOKIE_NAMES") or "").strip()
    if mode == "jwt":
        if not has_secret and not has_intro:
            logger.warning(
                "LEADERBOARD_AUTH_MODE=jwt but neither ANOTE_JWT_SECRET/JWT_SECRET_KEY nor "
                "ANOTE_TOKEN_INTROSPECT_URL is set — write routes will return 401."
            )
        logger.info(
            "Auth: mode=jwt jwt_secret=%s introspect=%s cookies=%s",
            "set" if has_secret else "off",
            "set" if has_intro else "off",
            cookies or "off",
        )
    else:
        logger.info("Auth: mode=off (set LEADERBOARD_AUTH_MODE=jwt to enforce on writes)")
