"""Tests for the meta endpoints: /healthz and /api/enums."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_healthz_does_not_require_auth(client: TestClient) -> None:
    # No Authorization header
    r = client.get("/healthz")
    assert r.status_code == 200


def test_enums_returns_full_reference_data(client: TestClient) -> None:
    r = client.get("/api/enums")
    assert r.status_code == 200

    data = r.json()

    assert set(data["cra_categories"]) == {"Travail", "Absence"}
    assert set(data["cra_activities"]["Travail"]) == {"Prestation", "HNO", "Astreinte"}
    assert set(data["cra_activities"]["Absence"]) == {
        "CP", "RTT", "Maladie", "Sans solde", "Autre",
    }
    assert "Restaurant" in data["expense_types"]
    assert "Indemnités kilométriques" in data["expense_types"]
    assert set(data["statuses"]) == {
        "Draft", "Pending", "Verified", "Validated", "Rejected",
    }


def test_enums_does_not_require_auth(client: TestClient) -> None:
    r = client.get("/api/enums")
    assert r.status_code == 200
