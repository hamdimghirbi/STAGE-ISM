"""Tests for /api/cra/events and /api/cra/month/* endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests._helpers import (
    create_event,
    delete_event,
    list_events,
    submit_month,
    update_event,
    upload_signature,
)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_event_returns_201_with_user_and_month(
    client: TestClient, auth_headers: dict[str, str], today: str, current_month: str
) -> None:
    event = create_event(client, auth_headers, start_date=today)
    assert event["activity"] == "Prestation"
    assert event["categorie"] == "Travail"
    assert event["month"] == current_month
    assert event["start_date"] == today
    assert event["end_date"] == today
    assert event["nb"] == 1.0
    assert isinstance(event["id"], int)
    assert isinstance(event["user_id"], int)


def test_create_event_multi_day_range(
    client: TestClient, auth_headers: dict[str, str], month_start: str, month_day_3: str
) -> None:
    event = create_event(
        client, auth_headers, start_date=month_start, end_date=month_day_3
    )
    assert event["start_date"] == month_start
    assert event["end_date"] == month_day_3


def test_create_event_half_day(
    client: TestClient, auth_headers: dict[str, str], today: str
) -> None:
    event = create_event(
        client, auth_headers, start_date=today, all_day=False, nb=0.5
    )
    assert event["nb"] == 0.5
    assert event["all_day"] is False


def test_create_event_absence_cp(
    client: TestClient, auth_headers: dict[str, str], today: str
) -> None:
    event = create_event(
        client, auth_headers, categorie="Absence", activity="CP", start_date=today
    )
    assert event["categorie"] == "Absence"
    assert event["activity"] == "CP"


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_events_returns_only_current_user_events_for_month(
    client: TestClient,
    auth_headers: dict[str, str],
    today: str,
    current_month: str,
) -> None:
    e = create_event(client, auth_headers, start_date=today)
    items = list_events(client, auth_headers, current_month)
    ids = [i["id"] for i in items]
    assert e["id"] in ids


def test_list_events_empty_for_far_past_month(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    items = list_events(client, auth_headers, "2000-01")
    assert items == []


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_update_event_partial(
    client: TestClient, auth_headers: dict[str, str], today: str
) -> None:
    e = create_event(client, auth_headers, start_date=today, description="initial")
    updated = update_event(client, auth_headers, e["id"], description="new desc")
    assert updated["description"] == "new desc"
    # untouched fields preserved
    assert updated["start_date"] == today


def test_update_event_recomputes_month_when_start_date_moves(
    client: TestClient, auth_headers: dict[str, str], today: str
) -> None:
    e = create_event(client, auth_headers, start_date=today)
    # Move to a fixed past date
    updated = update_event(
        client,
        auth_headers,
        e["id"],
        start_date="2025-01-15",
        end_date="2025-01-15",
    )
    assert updated["month"] == "2025-01"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_event_returns_204_and_is_gone(
    client: TestClient,
    auth_headers: dict[str, str],
    today: str,
    current_month: str,
) -> None:
    e = create_event(client, auth_headers, start_date=today)
    delete_event(client, auth_headers, e["id"])
    items = list_events(client, auth_headers, current_month)
    assert e["id"] not in [i["id"] for i in items]


# ---------------------------------------------------------------------------
# Month submit
# ---------------------------------------------------------------------------


def test_submit_month_moves_to_pending(
    client: TestClient,
    auth_headers: dict[str, str],
    today: str,
    current_month: str,
) -> None:
    create_event(client, auth_headers, start_date=today)
    month = submit_month(client, auth_headers, current_month)
    assert month["status"] == "Pending"
    assert month["submitted_at"] is not None
    assert month["month"] == current_month


def test_submit_month_with_reserves(
    client: TestClient, auth_headers: dict[str, str], current_month: str
) -> None:
    r = client.post(
        f"/api/cra/month/{current_month}/submit",
        json={
            "description_tasks": "Activités",
            "reserve_use_eur": 100.0,
            "reserve_use_days": 1.0,
            "reserve_save_eur": 50.0,
            "reserve_save_days": 0.5,
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["reserve_use_eur"] == 100.0
    assert data["reserve_use_days"] == 1.0
    assert data["reserve_save_eur"] == 50.0
    assert data["reserve_save_days"] == 0.5


def test_submit_already_pending_month_stays_pending(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
) -> None:
    submit_month(client, auth_headers, current_month)
    second = submit_month(client, auth_headers, current_month)
    assert second["status"] == "Pending"


# ---------------------------------------------------------------------------
# Signature upload
# ---------------------------------------------------------------------------


def test_upload_signature_stores_path(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    sample_png: bytes,
) -> None:
    month = upload_signature(client, auth_headers, current_month, sample_png)
    assert month["signature_path"] is not None
    assert "signatures" in month["signature_path"]
    assert month["signature_path"].endswith(".png")


def test_upload_signature_accepts_pdf(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    sample_pdf: bytes,
) -> None:
    r = client.post(
        f"/api/cra/month/{current_month}/signature",
        files={"file": ("sig.pdf", sample_pdf, "application/pdf")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["signature_path"].endswith(".pdf")
