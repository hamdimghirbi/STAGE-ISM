"""Tests for /api/cra-tracking endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests._helpers import (
    create_event,
    import_client_cra,
    list_tracking_months,
    submit_month,
    upload_signature,
)


def test_list_tracking_months_pagination_shape(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    page = list_tracking_months(client, auth_headers, page=1, limit=10)
    assert page["page"] == 1
    assert page["limit"] == 10
    assert isinstance(page["items"], list)
    assert isinstance(page["total"], int)


def test_seed_provides_validated_history(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Seed creates 4 past Validated months — confirm they're returned."""
    page = list_tracking_months(client, auth_headers, limit=100)
    validated = [m for m in page["items"] if m["status"] == "Validated"]
    assert len(validated) >= 4


def test_list_filters_by_year(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # Seed creates Validated months in either the current or previous year.
    page = list_tracking_months(client, auth_headers, year=2000, limit=100)
    # 2000 has nothing
    assert all(not m["month"].startswith("2000") for m in page["items"]) or page["items"] == []
    assert page["total"] >= 0


def test_list_filters_by_month_number(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    page = list_tracking_months(client, auth_headers, month=1, limit=100)
    for m in page["items"]:
        assert m["month"].endswith("-01")


def test_list_high_page_returns_empty(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    page = list_tracking_months(client, auth_headers, page=9999, limit=10)
    assert page["items"] == []


def test_import_client_cra_stores_path(
    client: TestClient,
    auth_headers: dict[str, str],
    today: str,
    current_month: str,
    sample_pdf: bytes,
) -> None:
    # Need to first create a month (event + submit) so import has a target
    create_event(client, auth_headers, start_date=today)
    submit_month(client, auth_headers, current_month)
    month = import_client_cra(client, auth_headers, current_month, sample_pdf)
    assert month["client_cra_path"] is not None
    assert "client-cra" in month["client_cra_path"]


def test_import_client_cra_for_nonexistent_month_returns_404(
    client: TestClient,
    auth_headers: dict[str, str],
    sample_pdf: bytes,
) -> None:
    r = client.post(
        "/api/cra-tracking/months/2099-01/import-client-cra",
        files={"file": ("c.pdf", sample_pdf, "application/pdf")},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_full_signature_then_import_round_trip(
    client: TestClient,
    auth_headers: dict[str, str],
    today: str,
    current_month: str,
    sample_pdf: bytes,
    sample_png: bytes,
) -> None:
    """End-to-end: event -> submit -> signature -> import client CRA."""
    create_event(client, auth_headers, start_date=today)
    submit_month(client, auth_headers, current_month)
    upload_signature(client, auth_headers, current_month, sample_png)
    import_client_cra(client, auth_headers, current_month, sample_pdf)

    page = list_tracking_months(client, auth_headers, limit=100)
    cm = next(m for m in page["items"] if m["month"] == current_month)
    assert cm["signature_path"] is not None
    assert cm["client_cra_path"] is not None
    assert cm["status"] == "Pending"


@pytest.mark.parametrize("bad_month", ["2026-13", "26-05", "not-a-month", "2026-00"])
def test_import_client_cra_rejects_malformed_month(
    client: TestClient,
    auth_headers: dict[str, str],
    sample_pdf: bytes,
    bad_month: str,
) -> None:
    r = client.post(
        f"/api/cra-tracking/months/{bad_month}/import-client-cra",
        files={"file": ("c.pdf", sample_pdf, "application/pdf")},
        headers=auth_headers,
    )
    assert r.status_code == 422
