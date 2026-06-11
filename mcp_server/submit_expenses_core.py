from __future__ import annotations

"""Core submission logic for posting expenses and CRA data to the Portalite API.

This module is intentionally kept separate from FastMCP so it can be tested
independently without a running MCP client. server.py is the thin wrapper
that exposes this logic as an MCP tool.

API endpoints called:
  POST /api/auth/login                  → get JWT token
  POST /api/expenses                    → create one expense (multipart form)
  POST /api/cra/events                  → create one CRA event (JSON)
  POST /api/cra/month/{month}/submit    → submit the monthly declaration (JSON)

Robustness features:
  - Retry with exponential backoff on transient errors (network, 5xx)
  - Timeout on all requests (default 30s, configurable via PORTALITE_TIMEOUT)
  - Input validation via Pydantic before any API call
  - Clear actionable error messages returned to the LLM — never raises
"""

import asyncio
import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional

import httpx

from schemas import (
    ConfirmedSubmission,
    CraEvent,
    CraEventResult,
    CraMonthResult,
    CraMonthSubmit,
    ExpenseItem,
    ExpenseResult,
    ExpenseType,
    SubmissionReport,
)

logger = logging.getLogger(__name__)

# Maximum allowed receipt file size: 10 MB
MAX_SIZE = 10 * 1024 * 1024

# Retry configuration for transient errors
MAX_RETRIES = 3          # maximum number of attempts per request
RETRY_BASE  = 1.0        # base delay in seconds (doubled on each retry)


# Return the Portalite API base URL.
# Can be overridden via the PORTALITE_BASE_URL environment variable for testing.
def _base_url() -> str:
    return os.getenv("PORTALITE_BASE_URL", "http://localhost:8005")


# Return the request timeout in seconds.
# Can be overridden via PORTALITE_TIMEOUT environment variable.
def _timeout() -> float:
    return float(os.getenv("PORTALITE_TIMEOUT", "30"))


# Return True if the HTTP status code is a transient error worth retrying.
# 5xx errors are server-side and may recover. Network errors are also transient.
def _is_transient(status_code: int) -> bool:
    return status_code >= 500


# Execute an async HTTP call with exponential backoff retry.
# Retries on: network errors (ConnectError, TimeoutException) and 5xx responses.
# Does NOT retry on: 4xx errors (bad input — retrying won't help).
# Waits RETRY_BASE * 2^attempt seconds between retries (1s, 2s, 4s...).
# Returns the last response or raises the last exception after MAX_RETRIES attempts.
async def _with_retry(call, label: str):
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = await call()
            # If server error, wait and retry
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

    # All retries exhausted — raise the last exception or return last response
    if last_exc:
        raise last_exc
    return resp


# Authenticate with Portalite and return a Bearer JWT token.
# Uses OAuth2PasswordRequestForm so credentials are sent as form data (not JSON)
# and the field is "username" (not "email") as required by FastAPI's OAuth2 form.
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


# Submit a single expense item to Portalite.
# If the expense has a receipt, it is uploaded as a multipart file attachment.
# If the file is too large (>10MB), the expense fails immediately without an API call.
# If the expense type requires a receipt but the file is not found on disk, it fails.
# Returns an ExpenseResult with status "ok" or "failed" and the created expense_id if successful.
async def _submit_one_expense(
    client: httpx.AsyncClient,
    token: str,
    index: int,
    expense: ExpenseItem,
) -> ExpenseResult:
    headers = {"Authorization": f"Bearer {token}"}

    # Build the form data payload matching POST /api/expenses fields
    data = {
        "type":               expense.type.value,
        "month":              expense.month,
        "total_amount":       str(expense.total_amount),
        "description":        expense.description,
        "billable_to_client": str(expense.billable_to_client).lower(),
        "comment":            expense.comment,
    }

    receipt_path = Path(expense.receipt_path) if expense.receipt_path else None

    # Check file size before uploading to avoid sending oversized files
    if receipt_path and receipt_path.exists() and receipt_path.stat().st_size > MAX_SIZE:
        return ExpenseResult(
            index=index,
            description=expense.description,
            total_amount=expense.total_amount,
            status="failed",
            error=f"File too large: {receipt_path.stat().st_size // 1024 // 1024}MB (max 10MB)",
            receipt_uploaded=False,
        )

    try:
        if receipt_path and receipt_path.exists():
            # Upload expense with receipt as multipart form data
            # mimetypes.guess_type detects PDF, PNG, JPG automatically
            mime, _ = mimetypes.guess_type(str(receipt_path))
            mime = mime or "application/octet-stream"
            with receipt_path.open("rb") as fh:
                file_content = fh.read()
            resp = await _with_retry(
                lambda: client.post(
                    "/api/expenses",
                    data=data,
                    files={"receipt": (receipt_path.name, file_content, mime)},
                    headers=headers,
                    timeout=_timeout(),
                ),
                label=f"expense[{index}] with receipt",
            )
        elif expense.type != ExpenseType.INDEMNITES_KM:
            # Non-KM expenses require a receipt — fail immediately if file not found
            return ExpenseResult(
                index=index,
                description=expense.description,
                total_amount=expense.total_amount,
                status="failed",
                error=f"Justificatif introuvable : '{expense.receipt_path}'",
                receipt_uploaded=False,
            )
        else:
            # INDEMNITES_KM — no receipt needed, submit without file
            resp = await _with_retry(
                lambda: client.post(
                    "/api/expenses",
                    data=data,
                    headers=headers,
                    timeout=_timeout(),
                ),
                label=f"expense[{index}] KM",
            )

        if resp.status_code in (200, 201):
            return ExpenseResult(
                index=index,
                description=expense.description,
                total_amount=expense.total_amount,
                status="ok",
                expense_id=resp.json().get("id"),
                # receipt_uploaded is True only if a file was actually sent
                receipt_uploaded=receipt_path is not None and receipt_path.exists(),
            )
        return ExpenseResult(
            index=index,
            description=expense.description,
            total_amount=expense.total_amount,
            status="failed",
            error=f"HTTP {resp.status_code} : {resp.text[:300]}",
            receipt_uploaded=False,
        )

    except httpx.TimeoutException:
        return ExpenseResult(
            index=index,
            description=expense.description,
            total_amount=expense.total_amount,
            status="failed",
            error="Request timed out after all retries — check your network connection.",
            receipt_uploaded=False,
        )
    except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
        return ExpenseResult(
            index=index,
            description=expense.description,
            total_amount=expense.total_amount,
            status="failed",
            error=f"Network error after all retries: {exc}. Check that Portalite is reachable.",
            receipt_uploaded=False,
        )
    except Exception as exc:
        logger.exception("Unexpected error submitting expense %d", index)
        return ExpenseResult(
            index=index,
            description=expense.description,
            total_amount=expense.total_amount,
            status="failed",
            error=str(exc),
            receipt_uploaded=False,
        )


# Submit a single CRA event (one day or a range of days) to Portalite.
# The event contains a category (Travail/Absence) and an activity (Prestation, CP, etc.).
# Returns a CraEventResult with the created event_id if successful.
async def _submit_one_cra_event(
    client: httpx.AsyncClient,
    token: str,
    index: int,
    event: CraEvent,
) -> CraEventResult:
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "categorie":   event.categorie.value,
        "activity":    event.activity.value,
        "start_date":  event.start_date,
        "end_date":    event.end_date,
        "nb":          event.nb,
        "all_day":     event.all_day,
        "description": event.description,
    }
    try:
        resp = await _with_retry(
            lambda: client.post(
                "/api/cra/events",
                json=payload,
                headers=headers,
                timeout=_timeout(),
            ),
            label=f"cra_event[{index}]",
        )
        if resp.status_code in (200, 201):
            return CraEventResult(
                index=index,
                start_date=event.start_date,
                end_date=event.end_date,
                activity=event.activity.value,
                status="ok",
                event_id=resp.json().get("id"),
            )
        return CraEventResult(
            index=index,
            start_date=event.start_date,
            end_date=event.end_date,
            activity=event.activity.value,
            status="failed",
            error=f"HTTP {resp.status_code} : {resp.text[:300]}",
        )
    except httpx.TimeoutException:
        return CraEventResult(
            index=index, start_date=event.start_date, end_date=event.end_date,
            activity=event.activity.value, status="failed",
            error="Request timed out after all retries — check your network connection.",
        )
    except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
        return CraEventResult(
            index=index, start_date=event.start_date, end_date=event.end_date,
            activity=event.activity.value, status="failed",
            error=f"Network error after all retries: {exc}.",
        )
    except Exception as exc:
        logger.exception("Unexpected error submitting CRA event %d", index)
        return CraEventResult(
            index=index, start_date=event.start_date, end_date=event.end_date,
            activity=event.activity.value, status="failed", error=str(exc),
        )


# Submit the monthly CRA declaration to Portalite.
# If cra_month is None (consultant only submitted expenses), this step is skipped.
# Returns a CraMonthResult with status "ok", "failed", or "skipped".
async def _submit_cra_month(
    client: httpx.AsyncClient,
    token: str,
    cra_month: Optional[CraMonthSubmit],
) -> CraMonthResult:
    if cra_month is None:
        return CraMonthResult(status="skipped")

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "description_tasks": cra_month.description_tasks,
        "reserve_use_eur":   cra_month.reserve_use_eur,
        "reserve_use_days":  cra_month.reserve_use_days,
        "reserve_save_eur":  cra_month.reserve_save_eur,
        "reserve_save_days": cra_month.reserve_save_days,
    }
    try:
        resp = await _with_retry(
            lambda: client.post(
                f"/api/cra/month/{cra_month.month}/submit",
                json=payload,
                headers=headers,
                timeout=_timeout(),
            ),
            label=f"cra_month[{cra_month.month}]",
        )
        if resp.status_code in (200, 201):
            return CraMonthResult(
                status="ok",
                month=cra_month.month,
                cra_month_id=resp.json().get("id"),
            )
        return CraMonthResult(
            status="failed",
            month=cra_month.month,
            error=f"HTTP {resp.status_code} : {resp.text[:300]}",
        )
    except httpx.TimeoutException:
        return CraMonthResult(
            status="failed", month=cra_month.month,
            error="Request timed out after all retries — check your network connection.",
        )
    except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
        return CraMonthResult(
            status="failed", month=cra_month.month,
            error=f"Network error after all retries: {exc}.",
        )
    except Exception as exc:
        logger.exception("Unexpected error submitting CRA month")
        return CraMonthResult(status="failed", month=cra_month.month, error=str(exc))


# Main entry point called by the submit_expenses MCP tool.
# Orchestrates the full submission flow:
#   1. Authenticate → get JWT token
#   2. Submit each expense (with receipt if available)
#   3. Submit each CRA event
#   4. Submit the monthly declaration
#   5. Build and return a SubmissionReport
#
# This function never raises exceptions — all errors are caught and returned
# in the SubmissionReport so Claude can always show a clear message to the consultant.
# If one expense fails, the others still get submitted (no blocking).
async def run_submission(
    submission: ConfirmedSubmission,
    email: str,
    password: str,
) -> SubmissionReport:
    async with httpx.AsyncClient(base_url=_base_url()) as client:

        # Step 1 — Authenticate. If this fails, return immediately with all items failed.
        try:
            token = await _login(client, email, password)
        except RuntimeError as exc:
            err = f"Erreur d'authentification : {exc}"
            return SubmissionReport(
                expenses_total=len(submission.expenses),
                expenses_submitted=0,
                expenses_failed=len(submission.expenses),
                cra_events_total=len(submission.cra_events),
                cra_events_submitted=0,
                cra_events_failed=len(submission.cra_events),
                expenses=[
                    ExpenseResult(index=i, description=e.description,
                                  total_amount=e.total_amount, status="failed", error=err)
                    for i, e in enumerate(submission.expenses)
                ],
                cra_events=[
                    CraEventResult(index=i, start_date=ev.start_date, end_date=ev.end_date,
                                   activity=ev.activity.value, status="failed", error=err)
                    for i, ev in enumerate(submission.cra_events)
                ],
                cra_month=CraMonthResult(status="failed", error=err),
                summary="Authentication failed - nothing was submitted.",
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            err = f"Network error during login: {exc}. Check that Portalite is reachable."
            return SubmissionReport(
                expenses_total=len(submission.expenses),
                expenses_submitted=0,
                expenses_failed=len(submission.expenses),
                cra_events_total=len(submission.cra_events),
                cra_events_submitted=0,
                cra_events_failed=len(submission.cra_events),
                expenses=[
                    ExpenseResult(index=i, description=e.description,
                                  total_amount=e.total_amount, status="failed", error=err)
                    for i, e in enumerate(submission.expenses)
                ],
                cra_events=[
                    CraEventResult(index=i, start_date=ev.start_date, end_date=ev.end_date,
                                   activity=ev.activity.value, status="failed", error=err)
                    for i, ev in enumerate(submission.cra_events)
                ],
                cra_month=CraMonthResult(status="failed", error=err),
                summary=f"Network error — nothing was submitted. {err}",
            )

        # Step 2 — Submit each expense. Failures are captured but do not stop the loop.
        expense_results: list[ExpenseResult] = []
        for i, expense in enumerate(submission.expenses):
            result = await _submit_one_expense(client, token, i, expense)
            expense_results.append(result)

        # Step 3 — Submit each CRA event.
        event_results: list[CraEventResult] = []
        for i, event in enumerate(submission.cra_events):
            result = await _submit_one_cra_event(client, token, i, event)
            event_results.append(result)

        # Step 4 — Submit the monthly declaration (skipped if not provided).
        cra_month_result = await _submit_cra_month(client, token, submission.cra_month)

    # Step 5 — Count results and build the summary string
    n_exp_ok   = sum(1 for r in expense_results if r.status == "ok")
    n_exp_fail = sum(1 for r in expense_results if r.status == "failed")
    n_evt_ok   = sum(1 for r in event_results   if r.status == "ok")
    n_evt_fail = sum(1 for r in event_results   if r.status == "failed")

    parts = []
    if submission.expenses:
        why = [r.error for r in expense_results if r.error]
        parts.append(f"{n_exp_ok} submitted, {n_exp_fail} failed, why: {why}")
    if submission.cra_events:
        why = [r.error for r in event_results if r.error]
        parts.append(f"{n_evt_ok} CRA events submitted, {n_evt_fail} failed, why: {why}")
    if cra_month_result.status == "ok":
        parts.append(f"CRA {cra_month_result.month} submitted")
    elif cra_month_result.status == "failed":
        parts.append(f"CRA month failed, why: {cra_month_result.error}")

    return SubmissionReport(
        expenses_total=len(submission.expenses),
        expenses_submitted=n_exp_ok,
        expenses_failed=n_exp_fail,
        cra_events_total=len(submission.cra_events),
        cra_events_submitted=n_evt_ok,
        cra_events_failed=n_evt_fail,
        expenses=expense_results,
        cra_events=event_results,
        cra_month=cra_month_result,
        summary=" | ".join(parts) if parts else "Nothing to submit.",
    )