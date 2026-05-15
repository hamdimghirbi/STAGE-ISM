"""Parametrized negative-path tests.

Each parametrized test collapses many similar negative cases into one
function. Read the parameter list as a table of (input -> expected).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# CRA event business-rule validation (400)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "categorie,activity",
    [
        ("Absence", "Prestation"),
        ("Absence", "HNO"),
        ("Absence", "Astreinte"),
        ("Travail", "CP"),
        ("Travail", "RTT"),
        ("Travail", "Maladie"),
    ],
)
def test_event_category_activity_mismatch_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
    today: str,
    categorie: str,
    activity: str,
) -> None:
    r = client.post(
        "/api/cra/events",
        json={
            "categorie": categorie,
            "activity": activity,
            "start_date": today,
            "end_date": today,
            "all_day": True,
            "nb": 1.0,
        },
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_event_end_before_start_returns_400(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    r = client.post(
        "/api/cra/events",
        json={
            "categorie": "Travail",
            "activity": "Prestation",
            "start_date": "2026-05-10",
            "end_date": "2026-05-05",
            "all_day": True,
            "nb": 1.0,
        },
        headers=auth_headers,
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# CRA event payload schema validation (422)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    ["categorie", "activity", "start_date", "end_date"],
)
def test_event_missing_required_field_returns_422(
    client: TestClient, auth_headers: dict[str, str], today: str, missing_field: str
) -> None:
    full_payload = {
        "categorie": "Travail",
        "activity": "Prestation",
        "start_date": today,
        "end_date": today,
        "all_day": True,
        "nb": 1.0,
    }
    full_payload.pop(missing_field)
    r = client.post("/api/cra/events", json=full_payload, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.parametrize(
    "bad_nb",
    [0, -1, 1.5, 2],  # nb must be in (0, 1]
)
def test_event_nb_out_of_range_returns_422(
    client: TestClient, auth_headers: dict[str, str], today: str, bad_nb: float
) -> None:
    r = client.post(
        "/api/cra/events",
        json={
            "categorie": "Travail",
            "activity": "Prestation",
            "start_date": today,
            "end_date": today,
            "nb": bad_nb,
        },
        headers=auth_headers,
    )
    assert r.status_code == 422


@pytest.mark.parametrize("bad_month", ["2026-13", "26-05", "2026/05", "not-month", "2026-00"])
def test_list_events_rejects_malformed_month(
    client: TestClient, auth_headers: dict[str, str], bad_month: str
) -> None:
    r = client.get(f"/api/cra/events?month={bad_month}", headers=auth_headers)
    assert r.status_code == 422


def test_update_event_not_found_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    r = client.put(
        "/api/cra/events/999999",
        json={"description": "ghost"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_delete_event_not_found_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    r = client.delete("/api/cra/events/999999", headers=auth_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Expense validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expense_type",
    [
        "Restaurant",
        "Titre de transport",
        "Telephonie",
        "Teletravail",
        "Materiel",
        "Autre",
    ],
)
def test_create_expense_missing_receipt_returns_400(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    expense_type: str,
) -> None:
    r = client.post(
        "/api/expenses",
        data={
            "type": expense_type,
            "month": current_month,
            "total_amount": "10.0",
        },
        headers=auth_headers,
    )
    assert r.status_code == 400


def test_create_expense_zero_amount_returns_422(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    sample_pdf: bytes,
) -> None:
    r = client.post(
        "/api/expenses",
        data={
            "type": "Restaurant",
            "month": current_month,
            "total_amount": "0",
        },
        files={"receipt": ("r.pdf", sample_pdf, "application/pdf")},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_update_expense_not_found_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    r = client.put(
        "/api/expenses/999999",
        json={"total_amount": 10.0},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_delete_expense_not_found_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    r = client.delete("/api/expenses/999999", headers=auth_headers)
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Filter validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_month", [0, 13, -1, 100])
def test_filter_rejects_invalid_month(
    client: TestClient,
    auth_headers: dict[str, str],
    current_year: int,
    bad_month: int,
) -> None:
    r = client.post(
        "/api/expenses/filter",
        json={"year": current_year, "month": bad_month},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_filter_missing_year_returns_422(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    r = client.post("/api/expenses/filter", json={"month": 5}, headers=auth_headers)
    assert r.status_code == 422


@pytest.mark.parametrize("bad_limit", [0, -1, 101, 1000])
def test_filter_invalid_limit_returns_422(
    client: TestClient,
    auth_headers: dict[str, str],
    current_year: int,
    bad_limit: int,
) -> None:
    r = client.post(
        "/api/expenses/filter",
        json={"year": current_year, "limit": bad_limit},
        headers=auth_headers,
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# File upload validation (415 / 413)
# ---------------------------------------------------------------------------


def test_signature_upload_rejects_unsupported_extension(
    client: TestClient, auth_headers: dict[str, str], current_month: str
) -> None:
    r = client.post(
        f"/api/cra/month/{current_month}/signature",
        files={"file": ("bad.exe", b"MZ\x90\x00", "application/octet-stream")},
        headers=auth_headers,
    )
    assert r.status_code == 415


def test_receipt_upload_rejects_unsupported_extension(
    client: TestClient, auth_headers: dict[str, str], current_month: str
) -> None:
    r = client.post(
        "/api/expenses",
        data={
            "type": "Restaurant",
            "month": current_month,
            "total_amount": "10.0",
        },
        files={"receipt": ("bad.txt", b"hello", "text/plain")},
        headers=auth_headers,
    )
    assert r.status_code == 415


def test_signature_upload_rejects_oversize_file(
    client: TestClient, auth_headers: dict[str, str], current_month: str
) -> None:
    # 6 MB > 5 MB limit
    big = b"\x00" * (6 * 1024 * 1024)
    r = client.post(
        f"/api/cra/month/{current_month}/signature",
        files={"file": ("big.pdf", big, "application/pdf")},
        headers=auth_headers,
    )
    assert r.status_code == 413


# ---------------------------------------------------------------------------
# Cross-resource auth (404 when accessing other-user data)
# ---------------------------------------------------------------------------


def test_protected_endpoints_require_auth(client: TestClient) -> None:
    """Spot-check: every protected route returns 401 without a token."""
    cases = [
        ("GET", "/api/auth/me"),
        ("GET", "/api/cra/events?month=2026-05"),
        ("POST", "/api/cra/events"),
        ("POST", "/api/cra/month/2026-05/submit"),
        ("GET", "/api/cra-tracking/months"),
        ("POST", "/api/expenses/filter"),
    ]
    for method, url in cases:
        r = client.request(method, url)
        assert r.status_code == 401, f"{method} {url} expected 401, got {r.status_code}"
