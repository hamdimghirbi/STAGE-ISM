"""End-to-end tests for the get_status MCP tool against the mock Portalite API.

These tests require the mock-api to be running on port 8005:
    cd mock-api && uv run python -m uvicorn app.main:app --reload --port 8005

Each test calls get_status() directly and verifies the returned StatusReport.
"""

from __future__ import annotations
import os, sys
from pathlib import Path
import pytest, httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from get_status_core import get_status

BASE_URL = os.getenv("PORTALITE_BASE_URL", "http://localhost:8005")
EMAIL    = os.getenv("PORTALITE_EMAIL",    "demo@cra.local")
PASSWORD = os.getenv("PORTALITE_PASSWORD", "demo1234")

pytestmark = pytest.mark.asyncio


# Check whether the mock API is reachable before running live integration tests.
async def _api_disponible() -> bool:
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{BASE_URL}/healthz", timeout=3)
            return r.status_code == 200
    except Exception:
        return False


@pytest.mark.asyncio
# Verify get_status returns a valid report without filtering by month.
# Expects at least some expenses and CRA months in the database from previous tests.
async def test_get_status_sans_filtre():
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    report = await get_status(EMAIL, PASSWORD)

    # The report should have a summary
    assert report.summary != ""
    # There should be expenses in the database from previous e2e tests
    assert len(report.expenses) > 0
    # Every expense must have a valid status
    valid_statuses = {"Draft", "Pending", "Verified", "Validated", "Rejected"}
    for expense in report.expenses:
        assert expense.status in valid_statuses


@pytest.mark.asyncio
# Verify get_status filters correctly when a specific month is provided.
# Only expenses and CRA months for 2026-05 should be returned.
async def test_get_status_avec_filtre_mois():
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    report = await get_status(EMAIL, PASSWORD, month="2026-05")

    # All returned expenses must belong to 2026-05
    for expense in report.expenses:
        assert expense.month == "2026-05", f"Expected 2026-05 but got {expense.month}"

    # All returned CRA months must be 2026-05
    for cra_month in report.cra_months:
        assert cra_month.month == "2026-05"


@pytest.mark.asyncio
# Verify the summary contains the correct counts for each status.
# The summary should mention approved, pending, and rejected counts.
async def test_get_status_summary_format():
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    report = await get_status(EMAIL, PASSWORD, month="2026-05")

    # Summary must mention expense counts
    assert "expenses" in report.summary
    assert "approved" in report.summary
    assert "pending" in report.summary
    assert "rejected" in report.summary


@pytest.mark.asyncio
# Verify CRA month status is returned correctly.
# The mock-api seeds validated months for 2026-04, 2026-03, 2026-02.
async def test_get_status_cra_months_valides():
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    report = await get_status(EMAIL, PASSWORD, month="2026-04")

    # 2026-04 should exist and be Validated (seeded by mock-api)
    assert len(report.cra_months) > 0
    assert report.cra_months[0].status == "Validated"
    assert report.cra_months[0].submitted_at is not None


@pytest.mark.asyncio
# Verify that invalid credentials return a clean error in the summary.
# Nothing should crash — auth failure is captured in the report.
async def test_get_status_mauvais_credentials():
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    report = await get_status("wrong@email.com", "wrongpass")

    assert report.expenses == []
    assert report.cra_months == []
    assert "Authentication failed" in report.summary


@pytest.mark.asyncio
# Verify that querying a month with no submissions returns an empty report.
# 2020-01 should have no data in the database.
async def test_get_status_mois_vide():
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    report = await get_status(EMAIL, PASSWORD, month="2020-01")

    assert report.expenses == []
    assert report.cra_months == []
    assert report.summary == "No submissions found."