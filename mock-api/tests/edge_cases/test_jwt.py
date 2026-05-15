"""JWT payload edge cases — tokens that pass signature check but fail content checks."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings


def _make_token(payload: dict) -> str:
    """Encode a JWT with the production secret. Lets us craft payloads the
    real `create_access_token` would never produce."""
    exp = datetime.now(tz=timezone.utc) + timedelta(minutes=5)
    return jwt.encode({"exp": exp, **payload}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def test_token_without_sub_returns_401(client: TestClient) -> None:
    token = _make_token({"role": "member"})  # no 'sub'
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_token_with_unknown_user_id_returns_401(client: TestClient) -> None:
    token = _make_token({"sub": "999999", "role": "member"})  # user doesn't exist
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.parametrize("bad_sub", ["abc", "not-a-number"])
def test_token_with_non_numeric_sub_returns_401(
    client: TestClient, bad_sub: str
) -> None:
    """Non-numeric `sub` claim is rejected as 401, not 500."""
    token = _make_token({"sub": bad_sub, "role": "member"})
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
