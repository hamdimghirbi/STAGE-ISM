"""Tests for robustness features: retry, timeout, and error handling.

These tests verify that the connector handles real-world failures gracefully:
- Network disconnection → clean error, not a crash
- Server 5xx errors → retry with exponential backoff
- Timeout → clear message returned to the LLM
- Bad inputs → rejected by Pydantic before hitting the API
"""

from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import ConfirmedSubmission, ExpenseItem, ExpenseType
from submit_expenses_core import run_submission, _with_retry, MAX_RETRIES


# ---------------------------------------------------------------------------
# _with_retry unit tests — no API needed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
# Verify that _with_retry returns immediately on a successful response (no retries).
async def test_retry_success_first_attempt():
    call_count = 0

    async def mock_call():
        nonlocal call_count
        call_count += 1
        return httpx.Response(201)

    resp = await _with_retry(mock_call, label="test")
    assert resp.status_code == 201
    assert call_count == 1  # only called once


@pytest.mark.asyncio
# Verify that _with_retry retries on 5xx responses and eventually returns the last response.
async def test_retry_on_5xx():
    call_count = 0

    async def mock_call():
        nonlocal call_count
        call_count += 1
        if call_count < MAX_RETRIES:
            return httpx.Response(500)
        return httpx.Response(201)

    with patch("submit_expenses_core.asyncio.sleep", new_callable=AsyncMock):
        resp = await _with_retry(mock_call, label="test")

    assert resp.status_code == 201
    assert call_count == MAX_RETRIES


@pytest.mark.asyncio
# Verify that _with_retry does NOT retry on 4xx responses (bad input).
async def test_no_retry_on_4xx():
    call_count = 0

    async def mock_call():
        nonlocal call_count
        call_count += 1
        return httpx.Response(422)

    resp = await _with_retry(mock_call, label="test")
    assert resp.status_code == 422
    assert call_count == 1  # no retry on 4xx


@pytest.mark.asyncio
# Verify that _with_retry retries on network errors (ConnectError).
async def test_retry_on_connect_error():
    call_count = 0

    async def mock_call():
        nonlocal call_count
        call_count += 1
        if call_count < MAX_RETRIES:
            raise httpx.ConnectError("Connection refused")
        return httpx.Response(201)

    with patch("submit_expenses_core.asyncio.sleep", new_callable=AsyncMock):
        resp = await _with_retry(mock_call, label="test")

    assert resp.status_code == 201
    assert call_count == MAX_RETRIES


# ---------------------------------------------------------------------------
# Integration tests — clean error messages on network failure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
# Verify that a network disconnection during submission returns a clean error report.
# The consultant should see a clear message, not a Python traceback.
async def test_network_disconnect_returns_clean_error():
    submission = ConfirmedSubmission(expenses=[
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05",
                    total_amount=45.0, description="Test")
    ])

    # Simulate network being completely unreachable
    with patch("submit_expenses_core.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.side_effect = httpx.ConnectError("Network unreachable")

        report = await run_submission(submission, "demo@cra.local", "demo1234")

    # Should return a clean report, not raise an exception
    assert report.expenses_submitted == 0
    assert report.expenses_failed == 1
    assert "Network error" in report.summary or "authentification" in report.summary.lower()


@pytest.mark.asyncio
# Verify that a timeout during submission returns a clear message.
async def test_timeout_returns_clean_error():
    submission = ConfirmedSubmission(expenses=[
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05",
                    total_amount=45.0, description="Test")
    ])

    with patch("submit_expenses_core.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post.side_effect = httpx.TimeoutException("Request timed out")

        report = await run_submission(submission, "demo@cra.local", "demo1234")

    assert report.expenses_submitted == 0
    assert report.expenses_failed == 1


# ---------------------------------------------------------------------------
# Input validation tests — Pydantic rejects bad data before hitting the API
# ---------------------------------------------------------------------------

# Verify that a negative amount is rejected before any API call.
def test_negative_amount_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05", total_amount=-10.0)


# Verify that an invalid month format is rejected before any API call.
def test_invalid_month_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026/05", total_amount=10.0)


# Verify that a non-KM expense without receipt is rejected before any API call.
def test_missing_receipt_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="receipt_path obligatoire"):
        ExpenseItem(type=ExpenseType.RESTAURANT, month="2026-05", total_amount=23.50)