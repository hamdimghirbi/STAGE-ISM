"""Shared pytest fixtures.

Each test gets an isolated SQLite DB and storage directory in tmp_path so
tests can't interfere with each other or with the dev `app.db`.
"""
from __future__ import annotations

import struct
import zlib
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine

import app.db as db_module
import app.seed as seed_module
from app.config import settings
from app.main import app as fastapi_app


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """TestClient backed by an isolated tmp SQLite DB and tmp storage dir.

    The app's lifespan creates tables and seeds the demo user on first request.
    """
    db_file = tmp_path / "test.db"
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()

    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Override the module-level engines referenced by db.py and seed.py.
    # Both modules bind `engine` at import time, so each needs its own patch.
    monkeypatch.setattr(db_module, "engine", test_engine)
    monkeypatch.setattr(seed_module, "engine", test_engine)

    # Point file uploads at the tmp dir.
    monkeypatch.setattr(settings, "storage_dir", str(storage_dir))

    with TestClient(fastapi_app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Bearer headers for the demo user (auto-seeded at lifespan startup)."""
    r = client.post(
        "/api/auth/login",
        data={"username": settings.demo_user_email, "password": settings.demo_user_password},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Date helpers - keep date-dependent tests deterministic-ish
# ---------------------------------------------------------------------------


@pytest.fixture
def today() -> str:
    return date.today().strftime("%Y-%m-%d")


@pytest.fixture
def current_month() -> str:
    return date.today().strftime("%Y-%m")


@pytest.fixture
def current_year() -> int:
    return date.today().year


@pytest.fixture
def month_start() -> str:
    return date.today().replace(day=1).strftime("%Y-%m-%d")


@pytest.fixture
def month_day_3() -> str:
    return date.today().replace(day=3).strftime("%Y-%m-%d")


@pytest.fixture
def month_day_5() -> str:
    return date.today().replace(day=5).strftime("%Y-%m-%d")


@pytest.fixture
def validated_month() -> str:
    """Previous month — seeded as Validated by seed_demo_data()."""
    today_d = date.today()
    if today_d.month > 1:
        return f"{today_d.year:04d}-{today_d.month - 1:02d}"
    return f"{today_d.year - 1:04d}-12"


@pytest.fixture
def validated_month_day(validated_month: str) -> str:
    """A YYYY-MM-DD string inside the validated month (15th)."""
    return f"{validated_month}-15"


# ---------------------------------------------------------------------------
# File fixtures - tiny valid PDF/PNG for multipart upload tests
# ---------------------------------------------------------------------------


def _minimal_pdf_bytes() -> bytes:
    body = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]"
        b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
        b"4 0 obj<</Length 30>>stream\nBT /F1 14 Tf 20 60 Td (Test) Tj ET\n"
        b"endstream endobj\n"
        b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    )
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    offset = 0
    for line in body.split(b"endobj\n")[:-1]:
        xref += f"{offset:010d} 00000 n \n".encode()
        offset += len(line) + len(b"endobj\n")
    trailer = b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n" + f"{len(body)}\n".encode() + b"%%EOF\n"
    return body + xref + trailer


def _tiny_png_bytes() -> bytes:
    """Smallest valid PNG (1x1 transparent)."""
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00\x00\x00\x00", 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


@pytest.fixture(scope="session")
def sample_pdf() -> bytes:
    return _minimal_pdf_bytes()


@pytest.fixture(scope="session")
def sample_png() -> bytes:
    return _tiny_png_bytes()
