from __future__ import annotations

"""Core logic for querying submission status from the Portalite API.

This module is intentionally kept separate from FastMCP so it can be tested
independently. server.py is the thin wrapper that exposes this as a get_status MCP tool.

API endpoints called:
  POST /api/auth/login              → get JWT token
  POST /api/expenses/filter         → get expenses with their status
  GET  /api/cra-tracking/months     → get CRA months with their status
"""

import datetime
import os
from typing import Optional

import httpx
from pydantic import BaseModel


# Return the Portalite API base URL.
# Can be overridden via the PORTALITE_BASE_URL environment variable for testing.
def _base_url() -> str:
    return os.getenv("PORTALITE_BASE_URL", "http://localhost:8005")


# Return the request timeout in seconds.
def _timeout() -> float:
    return float(os.getenv("PORTALITE_TIMEOUT", "30"))


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
# Claude shows the summary to the consultant and uses the detail lists
# to explain what is pending, approved, or rejected.
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
    resp = await client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        timeout=_timeout(),
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
# Never raises exceptions — auth failures are captured in the summary.
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

        headers = {"Authorization": f"Bearer {token}"}

        # Determine which year to query.
        # If a specific month is given, extract the year from it.
        # Otherwise default to the current year.
        year = int(month[:4]) if month else datetime.datetime.now().year

        # Step 2 — Fetch expenses for the year, filtered by month if provided.
        resp_exp = await client.post(
            "/api/expenses/filter",
            json={"year": year, "page": 1, "limit": 50},
            headers=headers,
            timeout=_timeout(),
        )

        expenses = []
        if resp_exp.status_code == 200:
            for item in resp_exp.json().get("items", []):
                # If a specific month was requested, skip expenses from other months
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

        # Step 3 — Fetch CRA month declarations, filtered by month if provided.
        # The endpoint returns a paginated list with items, total, page, pages, limit.
        resp_cra = await client.get(
            "/api/cra-tracking/months",
            headers=headers,
            timeout=_timeout(),
        )

        cra_months = []
        if resp_cra.status_code == 200:
            for item in resp_cra.json().get("items", []):
                # If a specific month was requested, skip other months
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