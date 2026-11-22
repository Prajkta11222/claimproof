"""JWT verification supporting JWKS (RS256) and HS256 fallback (A8)."""

from __future__ import annotations

from typing import Any

import httpx
import jwt as pyjwt
from fastapi import Depends, Request
from jwt import PyJWKClient

from app.core.config import Settings, get_settings
from app.core.errors import UnauthenticatedError

# Cache the JWKS client per URL
_jwks_clients: dict[str, PyJWKClient] = {}


def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    if jwks_url not in _jwks_clients:
        _jwks_clients[jwks_url] = PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_clients[jwks_url]


def verify_token(token: str, settings: Settings) -> dict[str, Any]:
    """Verify a Supabase JWT and return its claims.

    Supports JWKS (RS256, preferred) and HS256 fallback per A8.
    Verifies: exp, aud=authenticated, iss.
    """
    try:
        if settings.supabase_jwks_url:
            # JWKS / RS256
            jwks_client = _get_jwks_client(settings.supabase_jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            base_url = getattr(settings, "supabase_url", "").rstrip("/")
            issuer = getattr(settings, "supabase_jwt_issuer", "") or (
                f"{base_url}/auth/v1" if base_url else None
            )
            claims = pyjwt.decode(
                token,
                signing_key.key,
                algorithms=[
                    signing_key.algorithm_name
                    if signing_key.algorithm_name in ("RS256", "ES256")
                    else "RS256"
                ],
                audience=settings.supabase_jwt_audience,
                issuer=issuer,
                options={"require": ["exp", "sub"]},
            )
        elif settings.supabase_jwt_secret:
            # HS256 fallback
            base_url = getattr(settings, "supabase_url", "").rstrip("/")
            issuer = getattr(settings, "supabase_jwt_issuer", "") or (
                f"{base_url}/auth/v1" if base_url else None
            )
            claims = pyjwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=settings.supabase_jwt_audience,
                issuer=issuer,
                options={"require": ["exp", "sub"]},
            )
        else:
            raise UnauthenticatedError("JWT verification not configured.")

        if not claims.get("sub"):
            raise UnauthenticatedError("Token missing subject.")

        return claims

    except pyjwt.ExpiredSignatureError:
        raise UnauthenticatedError("Token has expired.")
    except pyjwt.InvalidAudienceError:
        raise UnauthenticatedError("Token audience mismatch.")
    except pyjwt.InvalidIssuerError:
        raise UnauthenticatedError("Token issuer mismatch.")
    except pyjwt.PyJWTError as e:
        raise UnauthenticatedError(f"Invalid token: {e}")
    except httpx.HTTPError:
        raise UnauthenticatedError("Could not verify token (JWKS fetch failed).")


def get_current_user(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    """FastAPI dependency: extract and verify JWT from Authorization header.

    Returns {"user_id": "<uuid>"}.
    Raises UnauthenticatedError (401) on failure.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise UnauthenticatedError("Missing or malformed Authorization header.")

    token = auth_header[7:]  # strip "Bearer "
    if not token:
        raise UnauthenticatedError("Empty token.")

    claims = verify_token(token, settings)
    return {"user_id": claims["sub"]}
