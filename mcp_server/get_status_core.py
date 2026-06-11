from __future__ import annotations

"""Core logic for querying submission status from the Portalite API.

This module is intentionally kept separate from FastMCP so it can be tested
independently. server.py is the thin wrapper that exposes this as a get_status MCP tool.

API endpoints called:
  POST /api/auth/login              → get JWT token
  POST /api/expenses/filter         → get expenses with their status
  GET  /api/cra-tracking/months     → get CRA months with their status

Robustness features:
  - Retry with exponential backoff on transient errors (network, 5xx)
  - Timeout on all requests (default 30s, configurable via PORTALITE_TIMEOUT)
  - Clear actionable error messages returned to the LLM — never raises
"""

import asyncio
import datetime
import logging
import os
from typing import Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Retry configuration for transient errors
MAX_RETRIES = 3
RETRY_BASE  = 1.0


# Return the Portalite API base URL.
def _base_url() -> str:
    return os.getenv("PORTALITE_BASE_URL", "http://localhost:8005")


# Return the request timeout in seconds.
def _timeout() -> float:
    return float(os.getenv("PORTALITE_TIMEOUT", "30"))


# Return True if the HTTP status code is a transient error worth retrying.
def _is_transient(status_code: int) -> bool:
    return status_code >= 500


# Execute an async HTTP call with exponential backoff retry.
# Retries on network errors and 5xx responses.
# Does NOT retry on 4xx errors (bad input — retrying won't help).
async def _with_retry(call, label: str):
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = await call()
            if _is_transient(resp.status_code):
                wait = RETRY_BASE * (2 ** attempt)
                logger.warning(
                    "%s — HTTP %d, retrying in %.1fs (attempt %d/%d)",
                    label, resp.status_code, wait, attempt + 1, MAX_RETRIES,
                )
                await asyncio.sleep(wait)
                continue
            return resp
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            wait = RETRY_BASE * (2 ** attempt)
            logger.warning(
                "%s — %s, retrying in %.1fs (attempt %d/%d)",
                label, type(exc).__name__, wait, attempt + 1, MAX_RETRIES,
            )
            await asyncio.sleep(wait)

    if last_exc:
        raise last_exc
    return resp


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

# Status of one expense as returned by Portalite.
# status can be: Draft, Pending, Verified, Validated, Rejected
class ExpenseStatus(BaseModel):
    id: int
    month: str
    type: str
    description: str
    total_amount: float
    status: str
    created_at: str


# Status of one CRA month declaration as returned by Portalite.
# submitted_at and validated_at are None if not yet submitted/validated.
class CraMonthStatus(BaseModel):
    id: int
    month: str
    status: str
    description_tasks: str
    submitted_at: Optional[str] = None
    validated_at: Optional[str] = None


# Full status report returned by the get_status MCP tool.
class StatusReport(BaseModel):
    expenses: list[ExpenseStatus]
    cra_months: list[CraMonthStatus]
    summary: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Authenticate with Portalite and return a Bearer JWT token.
# Uses OAuth2PasswordRequestForm — credentials sent as form data, field is "username".
async def _login(client: httpx.AsyncClient, email: str, password: str) -> str:
    resp = await _with_retry(
        lambda: client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
            timeout=_timeout(),
        ),
        label="login",
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Echec login ({resp.status_code}) : {resp.text[:200]}")
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

# Query Portalite for the status of recent expense and CRA submissions.
# If month is provided (format YYYY-MM), only that month's data is returned.
# If month is None, all submissions for the current year are returned.
#
# Returns a StatusReport with:
# - expenses: list of expenses with their current status
# - cra_months: list of CRA month declarations with their status
# - summary: human-readable one-liner showing counts by status
#
# Never raises exceptions — all errors are captured in the summary.
async def get_status(
    email: str,
    password: str,
    month: Optional[str] = None,
) -> StatusReport:
    async with httpx.AsyncClient(base_url=_base_url()) as client:

        # Step 1 — Authenticate. If this fails return an empty report with error message.
        try:
            token = await _login(client, email, password)
        except RuntimeError as exc:
            return StatusReport(
                expenses=[],
                cra_months=[],
                summary=f"Authentication failed: {exc}",
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            return StatusReport(
                expenses=[],
                cra_months=[],
                summary=f"Network error — cannot reach Portalite: {exc}. Check your connection.",
            )

        headers = {"Authorization": f"Bearer {token}"}

        # Determine which year to query.
        year = int(month[:4]) if month else datetime.datetime.now().year

        # Step 2 — Fetch expenses for the year, filtered by month if provided.
        expenses = []
        try:
            resp_exp = await _with_retry(
                lambda: client.post(
                    "/api/expenses/filter",
                    json={"year": year, "page": 1, "limit": 50},
                    headers=headers,
                    timeout=_timeout(),
                ),
                label="expenses/filter",
            )
            if resp_exp.status_code == 200:
                for item in resp_exp.json().get("items", []):
                    if month and not item["month"].startswith(month):
                        continue
                    expenses.append(ExpenseStatus(
                        id=item["id"],
                        month=item["month"],
                        type=item["type"],
                        description=item["description"],
                        total_amount=item["total_amount"],
                        status=item["status"],
                        created_at=item["created_at"],
                    ))
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("Could not fetch expenses: %s", exc)

        # Step 3 — Fetch CRA month declarations, filtered by month if provided.
        cra_months = []
        try:
            resp_cra = await _with_retry(
                lambda: client.get(
                    "/api/cra-tracking/months",
                    headers=headers,
                    timeout=_timeout(),
                ),
                label="cra-tracking/months",
            )
            if resp_cra.status_code == 200:
                for item in resp_cra.json().get("items", []):
                    if month and item["month"] != month:
                        continue
                    cra_months.append(CraMonthStatus(
                        id=item["id"],
                        month=item["month"],
                        status=item["status"],
                        description_tasks=item.get("description_tasks", ""),
                        submitted_at=item.get("submitted_at") or None,
                        validated_at=item.get("validated_at") or None,
                    ))
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("Could not fetch CRA months: %s", exc)

    # Step 4 — Count expenses by status and build the summary string
    pending  = sum(1 for e in expenses if e.status == "Pending")
    approved = sum(1 for e in expenses if e.status == "Validated")
    rejected = sum(1 for e in expenses if e.status == "Rejected")

    parts = []
    if expenses:
        parts.append(
            f"{len(expenses)} expenses: {approved} approved, {pending} pending, {rejected} rejected"
        )
    if cra_months:
        parts.append(
            f"{len(cra_months)} CRA months: " +
            ", ".join(f"{c.month} ({c.status})" for c in cra_months)
        )

    return StatusReport(
        expenses=expenses,
        cra_months=cra_months,
        summary=" | ".join(parts) if parts else "No submissions found.",
    )