from __future__ import annotations

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

MAX_SIZE = 10 * 1024 * 1024


def _base_url() -> str:
    return os.getenv("PORTALITE_BASE_URL", "http://localhost:8005")


def _timeout() -> float:
    return float(os.getenv("PORTALITE_TIMEOUT", "30"))


async def _login(client: httpx.AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/auth/login",
        data={"username": email, "password": password},
        timeout=_timeout(),
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Echec login ({resp.status_code}) : {resp.text[:200]}")
    return resp.json()["access_token"]


async def _submit_one_expense(
    client: httpx.AsyncClient,
    token: str,
    index: int,
    expense: ExpenseItem,
) -> ExpenseResult:
    headers = {"Authorization": f"Bearer {token}"}

    data = {
        "type":               expense.type.value,
        "month":              expense.month,
        "total_amount":       str(expense.total_amount),
        "description":        expense.description,
        "billable_to_client": str(expense.billable_to_client).lower(),
        "comment":            expense.comment,
    }

    receipt_path = Path(expense.receipt_path) if expense.receipt_path else None

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
            mime, _ = mimetypes.guess_type(str(receipt_path))
            mime = mime or "application/octet-stream"
            with receipt_path.open("rb") as fh:
                resp = await client.post(
                    "/api/expenses",
                    data=data,
                    files={"receipt": (receipt_path.name, fh, mime)},
                    headers=headers,
                    timeout=_timeout(),
                )
        elif expense.type != ExpenseType.INDEMNITES_KM:
            return ExpenseResult(
                index=index,
                description=expense.description,
                total_amount=expense.total_amount,
                status="failed",
                error=f"Justificatif introuvable : '{expense.receipt_path}'",
                receipt_uploaded=False,
            )
        else:
            resp = await client.post(
                "/api/expenses",
                data=data,
                headers=headers,
                timeout=_timeout(),
            )

        if resp.status_code in (200, 201):
            return ExpenseResult(
                index=index,
                description=expense.description,
                total_amount=expense.total_amount,
                status="ok",
                expense_id=resp.json().get("id"),
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
            error="Timeout",
            receipt_uploaded=False,
        )
    except Exception as exc:
        logger.exception("Erreur inattendue note de frais %d", index)
        return ExpenseResult(
            index=index,
            description=expense.description,
            total_amount=expense.total_amount,
            status="failed",
            error=str(exc),
            receipt_uploaded=False,
        )


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
        resp = await client.post(
            "/api/cra/events",
            json=payload,
            headers=headers,
            timeout=_timeout(),
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
            activity=event.activity.value, status="failed", error="Timeout",
        )
    except Exception as exc:
        logger.exception("Erreur inattendue evenement CRA %d", index)
        return CraEventResult(
            index=index, start_date=event.start_date, end_date=event.end_date,
            activity=event.activity.value, status="failed", error=str(exc),
        )


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
        resp = await client.post(
            f"/api/cra/month/{cra_month.month}/submit",
            json=payload,
            headers=headers,
            timeout=_timeout(),
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
        return CraMonthResult(status="failed", month=cra_month.month, error="Timeout")
    except Exception as exc:
        logger.exception("Erreur inattendue soumission mois CRA")
        return CraMonthResult(status="failed", month=cra_month.month, error=str(exc))


async def run_submission(
    submission: ConfirmedSubmission,
    email: str,
    password: str,
) -> SubmissionReport:
    async with httpx.AsyncClient(base_url=_base_url()) as client:

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

        expense_results: list[ExpenseResult] = []
        for i, expense in enumerate(submission.expenses):
            result = await _submit_one_expense(client, token, i, expense)
            expense_results.append(result)

        event_results: list[CraEventResult] = []
        for i, event in enumerate(submission.cra_events):
            result = await _submit_one_cra_event(client, token, i, event)
            event_results.append(result)

        cra_month_result = await _submit_cra_month(client, token, submission.cra_month)

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