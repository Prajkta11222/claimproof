from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.errors import UnauthenticatedError
from app.core.security import verify_token


class SecuritySettings:
    supabase_jwks_url = None
    supabase_jwt_secret = "test-secret-for-hs256-with-32bytes!"
    supabase_jwt_audience = "authenticated"
    supabase_jwt_issuer = ""
    supabase_url = "https://example.supabase.co"


def _token(**claims):
    payload = {
        "sub": "user-1",
        "aud": "authenticated",
        "iss": "https://example.supabase.co/auth/v1",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    payload.update(claims)
    return jwt.encode(
        payload,
        "test-secret-for-hs256-with-32bytes!",
        algorithm="HS256",
    )


def test_verify_token_accepts_valid_user_token():
    claims = verify_token(_token(), SecuritySettings())
    assert claims["sub"] == "user-1"


def test_verify_token_rejects_expired_token():
    token = _token(exp=datetime.now(timezone.utc) - timedelta(seconds=1))
    with pytest.raises(UnauthenticatedError):
        verify_token(token, SecuritySettings())


def test_verify_token_rejects_wrong_audience():
    token = _token(aud="anon")
    with pytest.raises(UnauthenticatedError):
        verify_token(token, SecuritySettings())
