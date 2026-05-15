"""Tests for /api/auth endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings


def test_login_with_demo_credentials_returns_jwt(client: TestClient) -> None:
    r = client.post(
        "/api/auth/login",
        data={"username": settings.demo_user_email, "password": settings.demo_user_password},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20


def test_login_with_wrong_password_returns_401(client: TestClient) -> None:
    r = client.post(
        "/api/auth/login",
        data={"username": settings.demo_user_email, "password": "wrong"},
    )
    assert r.status_code == 401


def test_login_with_unknown_email_returns_401(client: TestClient) -> None:
    r = client.post(
        "/api/auth/login",
        data={"username": "nobody@nowhere.com", "password": "demo1234"},
    )
    assert r.status_code == 401


def test_me_returns_current_user(client: TestClient, auth_headers: dict[str, str]) -> None:
    r = client.get("/api/auth/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == settings.demo_user_email
    assert data["role"] == "member"
    assert data["full_name"] == settings.demo_user_fullname
    assert isinstance(data["id"], int)


def test_me_without_token_returns_401(client: TestClient) -> None:
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_malformed_token_returns_401(client: TestClient) -> None:
    r = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert r.status_code == 401


@pytest.mark.parametrize("bad_header", ["", "Bearer", "Basic abc", "bearer xyz"])
def test_me_with_bad_authorization_header_returns_401(
    client: TestClient, bad_header: str
) -> None:
    r = client.get("/api/auth/me", headers={"Authorization": bad_header})
    assert r.status_code == 401
