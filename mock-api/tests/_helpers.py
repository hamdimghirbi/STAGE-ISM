"""Helper functions to keep scenario tests readable.

Each helper makes an API call and returns the parsed JSON (or raises if the
response is not what was expected). Use these to write end-to-end flows that
read like prose.
"""
from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def create_event(
    client: TestClient,
    headers: dict[str, str],
    *,
    categorie: str = "Travail",
    activity: str = "Prestation",
    start_date: str,
    end_date: str | None = None,
    all_day: bool = True,
    nb: float = 1.0,
    description: str = "",
) -> dict[str, Any]:
    payload = {
        "categorie": categorie,
        "activity": activity,
        "start_date": start_date,
        "end_date": end_date or start_date,
        "all_day": all_day,
        "nb": nb,
        "description": description,
    }
    r = client.post("/api/cra/events", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def update_event(
    client: TestClient,
    headers: dict[str, str],
    event_id: int,
    **changes: Any,
) -> dict[str, Any]:
    r = client.put(f"/api/cra/events/{event_id}", json=changes, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def delete_event(
    client: TestClient, headers: dict[str, str], event_id: int
) -> None:
    r = client.delete(f"/api/cra/events/{event_id}", headers=headers)
    assert r.status_code == 204, r.text


def list_events(
    client: TestClient, headers: dict[str, str], month: str
) -> list[dict[str, Any]]:
    r = client.get(f"/api/cra/events?month={month}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def submit_month(
    client: TestClient,
    headers: dict[str, str],
    month: str,
    description_tasks: str = "Activités du mois",
) -> dict[str, Any]:
    r = client.post(
        f"/api/cra/month/{month}/submit",
        json={
            "description_tasks": description_tasks,
            "reserve_use_eur": 0,
            "reserve_use_days": 0,
            "reserve_save_eur": 0,
            "reserve_save_days": 0,
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r.json()


def upload_signature(
    client: TestClient,
    headers: dict[str, str],
    month: str,
    png_bytes: bytes,
) -> dict[str, Any]:
    r = client.post(
        f"/api/cra/month/{month}/signature",
        files={"file": ("signature.png", png_bytes, "image/png")},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r.json()


def create_expense(
    client: TestClient,
    headers: dict[str, str],
    *,
    type: str,
    month: str,
    total_amount: float,
    description: str = "",
    billable_to_client: bool = False,
    comment: str = "",
    receipt: tuple[str, bytes, str] | None = None,
) -> dict[str, Any]:
    data = {
        "type": type,
        "month": month,
        "description": description,
        "total_amount": str(total_amount),
        "billable_to_client": str(billable_to_client).lower(),
        "comment": comment,
    }
    files = {"receipt": receipt} if receipt else None
    r = client.post("/api/expenses", data=data, files=files, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def update_expense(
    client: TestClient,
    headers: dict[str, str],
    expense_id: int,
    **changes: Any,
) -> dict[str, Any]:
    r = client.put(f"/api/expenses/{expense_id}", json=changes, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def delete_expense(
    client: TestClient, headers: dict[str, str], expense_id: int
) -> None:
    r = client.delete(f"/api/expenses/{expense_id}", headers=headers)
    assert r.status_code == 204, r.text


def filter_expenses(
    client: TestClient,
    headers: dict[str, str],
    **filters: Any,
) -> dict[str, Any]:
    filters.setdefault("page", 1)
    filters.setdefault("limit", 10)
    r = client.post("/api/expenses/filter", json=filters, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def list_tracking_months(
    client: TestClient,
    headers: dict[str, str],
    **params: Any,
) -> dict[str, Any]:
    r = client.get("/api/cra-tracking/months", params=params, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def import_client_cra(
    client: TestClient,
    headers: dict[str, str],
    month: str,
    pdf_bytes: bytes,
) -> dict[str, Any]:
    r = client.post(
        f"/api/cra-tracking/months/{month}/import-client-cra",
        files={"file": ("client_cra.pdf", pdf_bytes, "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r.json()
