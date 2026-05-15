"""Tests for /api/expenses endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests._helpers import (
    create_expense,
    delete_expense,
    filter_expenses,
    update_expense,
)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_restaurant_with_receipt_returns_201(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    sample_pdf: bytes,
) -> None:
    expense = create_expense(
        client,
        auth_headers,
        type="Restaurant",
        month=current_month,
        total_amount=42.5,
        billable_to_client=True,
        receipt=("receipt.pdf", sample_pdf, "application/pdf"),
    )
    assert expense["type"] == "Restaurant"
    assert expense["total_amount"] == 42.5
    assert expense["billable_to_client"] is True
    assert expense["receipt_path"] is not None
    assert expense["status"] == "Pending"


def test_create_km_without_receipt_returns_201(
    client: TestClient, auth_headers: dict[str, str], current_month: str
) -> None:
    expense = create_expense(
        client,
        auth_headers,
        type="Indemnités kilométriques",
        month=current_month,
        total_amount=50.0,
    )
    assert expense["type"] == "Indemnités kilométriques"
    assert expense["receipt_path"] is None


# All expense types that require a receipt
RECEIPT_REQUIRED_TYPES = [
    "Restaurant",
    "Titre de transport",
    "Telephonie",
    "Teletravail",
    "Materiel",
    "Autre",
]


@pytest.mark.parametrize("expense_type", RECEIPT_REQUIRED_TYPES)
def test_create_each_receipt_required_type_works(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    sample_pdf: bytes,
    expense_type: str,
) -> None:
    expense = create_expense(
        client,
        auth_headers,
        type=expense_type,
        month=current_month,
        total_amount=10.0,
        receipt=("r.pdf", sample_pdf, "application/pdf"),
    )
    assert expense["type"] == expense_type
    assert expense["status"] == "Pending"


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_update_expense_amount(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    sample_pdf: bytes,
) -> None:
    e = create_expense(
        client,
        auth_headers,
        type="Restaurant",
        month=current_month,
        total_amount=20.0,
        receipt=("r.pdf", sample_pdf, "application/pdf"),
    )
    updated = update_expense(client, auth_headers, e["id"], total_amount=42.5)
    assert updated["total_amount"] == 42.5


def test_update_expense_multiple_fields(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    sample_pdf: bytes,
) -> None:
    e = create_expense(
        client,
        auth_headers,
        type="Restaurant",
        month=current_month,
        total_amount=20.0,
        receipt=("r.pdf", sample_pdf, "application/pdf"),
    )
    updated = update_expense(
        client,
        auth_headers,
        e["id"],
        total_amount=99.99,
        description="updated desc",
        comment="updated comment",
        billable_to_client=True,
    )
    assert updated["total_amount"] == 99.99
    assert updated["description"] == "updated desc"
    assert updated["comment"] == "updated comment"
    assert updated["billable_to_client"] is True


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_expense_returns_204(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    sample_pdf: bytes,
) -> None:
    e = create_expense(
        client,
        auth_headers,
        type="Restaurant",
        month=current_month,
        total_amount=10.0,
        receipt=("r.pdf", sample_pdf, "application/pdf"),
    )
    delete_expense(client, auth_headers, e["id"])
    # confirm gone via filter
    page = filter_expenses(
        client, auth_headers, year=int(current_month[:4]), limit=100
    )
    assert e["id"] not in [x["id"] for x in page["items"]]


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------


def test_filter_by_year(
    client: TestClient, auth_headers: dict[str, str], current_year: int
) -> None:
    page = filter_expenses(client, auth_headers, year=current_year)
    assert "items" in page
    assert page["page"] == 1
    assert page["limit"] == 10


def test_filter_by_type_returns_only_that_type(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    current_year: int,
    sample_pdf: bytes,
) -> None:
    create_expense(
        client, auth_headers, type="Restaurant", month=current_month,
        total_amount=10.0, receipt=("r.pdf", sample_pdf, "application/pdf"),
    )
    create_expense(
        client, auth_headers, type="Indemnités kilométriques",
        month=current_month, total_amount=50.0,
    )
    page = filter_expenses(client, auth_headers, year=current_year, type="Restaurant")
    assert all(x["type"] == "Restaurant" for x in page["items"])


def test_filter_by_status_pending(
    client: TestClient, auth_headers: dict[str, str], current_year: int
) -> None:
    page = filter_expenses(client, auth_headers, year=current_year, status="Pending")
    assert all(x["status"] == "Pending" for x in page["items"])


def test_filter_by_billable_true(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    current_year: int,
    sample_pdf: bytes,
) -> None:
    create_expense(
        client, auth_headers, type="Restaurant", month=current_month,
        total_amount=10.0, billable_to_client=True,
        receipt=("r.pdf", sample_pdf, "application/pdf"),
    )
    page = filter_expenses(client, auth_headers, year=current_year, billable=True)
    assert all(x["billable_to_client"] is True for x in page["items"])


def test_filter_pagination_limit_1(
    client: TestClient, auth_headers: dict[str, str], current_year: int
) -> None:
    page = filter_expenses(client, auth_headers, year=current_year, limit=1)
    assert len(page["items"]) <= 1
    assert page["limit"] == 1


def test_filter_high_page_returns_empty(
    client: TestClient, auth_headers: dict[str, str], current_year: int
) -> None:
    page = filter_expenses(client, auth_headers, year=current_year, page=9999)
    assert page["items"] == []


def test_filter_by_year_and_month_narrows_results(
    client: TestClient,
    auth_headers: dict[str, str],
    current_month: str,
    current_year: int,
    sample_pdf: bytes,
) -> None:
    create_expense(
        client, auth_headers, type="Restaurant", month=current_month,
        total_amount=10.0, receipt=("r.pdf", sample_pdf, "application/pdf"),
    )
    cur_month_num = int(current_month.split("-")[1])
    page = filter_expenses(client, auth_headers, year=current_year, month=cur_month_num)
    # All returned items must be in that exact YYYY-MM
    for item in page["items"]:
        assert item["month"] == current_month
