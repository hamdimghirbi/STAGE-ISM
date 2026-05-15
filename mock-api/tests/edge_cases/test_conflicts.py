"""Tests for 409 Conflict paths — operations blocked by Validated state."""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests._helpers import create_event, filter_expenses


# ---------------------------------------------------------------------------
# CRA — Validated month blocks event creation & re-submission
# ---------------------------------------------------------------------------


def test_create_event_on_validated_month_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
    validated_month_day: str,
) -> None:
    r = client.post(
        "/api/cra/events",
        json={
            "categorie": "Travail",
            "activity": "Prestation",
            "start_date": validated_month_day,
            "end_date": validated_month_day,
            "all_day": True,
            "nb": 1.0,
        },
        headers=auth_headers,
    )
    assert r.status_code == 409


def test_submit_validated_month_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
    validated_month: str,
) -> None:
    r = client.post(
        f"/api/cra/month/{validated_month}/submit",
        json={"description_tasks": "shouldn't work"},
        headers=auth_headers,
    )
    assert r.status_code == 409


# ---------------------------------------------------------------------------
# CRA — PUT event re-validates category/activity and date order
# ---------------------------------------------------------------------------


def test_update_event_to_bad_end_date_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
    today: str,
) -> None:
    e = create_event(client, auth_headers, start_date=today)
    r = client.put(
        f"/api/cra/events/{e['id']}",
        json={"end_date": "2000-01-01"},  # before start_date
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_update_event_to_mismatched_activity_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
    today: str,
) -> None:
    e = create_event(client, auth_headers, start_date=today)  # Travail/Prestation
    r = client.put(
        f"/api/cra/events/{e['id']}",
        json={"activity": "CP"},  # CP is Absence-only
        headers=auth_headers,
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# Expenses — Validated state blocks update & delete
# ---------------------------------------------------------------------------


def test_update_validated_expense_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
    current_year: int,
) -> None:
    # Seed creates one Validated Telephonie expense
    page = filter_expenses(client, auth_headers, year=current_year, status="Validated", limit=100)
    assert page["items"], "expected seed to include a Validated expense"
    validated_id = page["items"][0]["id"]

    r = client.put(
        f"/api/expenses/{validated_id}",
        json={"total_amount": 99.99},
        headers=auth_headers,
    )
    assert r.status_code == 409


def test_delete_validated_expense_returns_409(
    client: TestClient,
    auth_headers: dict[str, str],
    current_year: int,
) -> None:
    page = filter_expenses(client, auth_headers, year=current_year, status="Validated", limit=100)
    assert page["items"]
    validated_id = page["items"][0]["id"]

    r = client.delete(f"/api/expenses/{validated_id}", headers=auth_headers)
    assert r.status_code == 409
