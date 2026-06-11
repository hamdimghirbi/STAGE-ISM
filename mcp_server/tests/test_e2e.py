from __future__ import annotations
import os, sys
from pathlib import Path
import pytest, httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import (
    ConfirmedSubmission, CraActivity, CraCategory, CraEvent,
    CraMonthSubmit, ExpenseItem, ExpenseType,
)
from submit_expenses_core import run_submission

BASE_URL = os.getenv("PORTALITE_BASE_URL", "http://localhost:8005")
EMAIL    = os.getenv("PORTALITE_EMAIL",    "demo@cra.local")
PASSWORD = os.getenv("PORTALITE_PASSWORD", "demo1234")

pytestmark = pytest.mark.asyncio


async def _api_disponible() -> bool:
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{BASE_URL}/healthz", timeout=3)
            return r.status_code == 200
    except Exception:
        return False


@pytest.mark.asyncio
async def test_km_sans_recu():
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    s = ConfirmedSubmission(expenses=[
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05",
                    total_amount=45.0, description="Trajet Paris-Versailles")
    ])
    report = await run_submission(s, EMAIL, PASSWORD)

    assert report.expenses_submitted == 1, report.summary
    assert report.expenses_failed == 0
    assert report.expenses[0].expense_id is not None


@pytest.mark.asyncio
async def test_restauration_avec_recu(tmp_path):
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    recu = tmp_path / "recu.pdf"
    recu.write_bytes(b"%PDF-1.4 fake receipt")

    s = ConfirmedSubmission(expenses=[
        ExpenseItem(type=ExpenseType.RESTAURANT, month="2026-05",
                    total_amount=23.50, description="Dejeuner client",
                    receipt_path=str(recu))
    ])
    report = await run_submission(s, EMAIL, PASSWORD)

    assert report.expenses_submitted == 1, report.summary
    assert report.expenses[0].expense_id is not None


@pytest.mark.asyncio
async def test_cra_event():
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    s = ConfirmedSubmission(cra_events=[
        CraEvent(categorie=CraCategory.TRAVAIL, activity=CraActivity.PRESTATION,
                 start_date="2026-05-05", end_date="2026-05-09",
                 description="Mission client Acme")
    ])
    report = await run_submission(s, EMAIL, PASSWORD)

    assert report.cra_events_submitted == 1, report.summary
    assert report.cra_events[0].event_id is not None


@pytest.mark.asyncio
async def test_workflow_mensuel_complet(tmp_path):
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    recu = tmp_path / "hotel.pdf"
    recu.write_bytes(b"%PDF-1.4 hotel invoice")

    s = ConfirmedSubmission(
        expenses=[
            ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05",
                        total_amount=36.0, description="Voiture client"),
            ExpenseItem(type=ExpenseType.TITRE_TRANSPORT, month="2026-05",
                        total_amount=95.0, description="Train Lyon",
                        receipt_path=str(recu)),
        ],
        cra_events=[
            CraEvent(categorie=CraCategory.TRAVAIL, activity=CraActivity.PRESTATION,
                     start_date="2026-05-05", end_date="2026-05-09"),
            CraEvent(categorie=CraCategory.ABSENCE, activity=CraActivity.CP,
                     start_date="2026-05-12", end_date="2026-05-12"),
        ],
        cra_month=CraMonthSubmit(month="2026-05",
                                 description_tasks="Migration BDD client Acme"),
    )
    report = await run_submission(s, EMAIL, PASSWORD)

    assert report.expenses_submitted == 2,  report.summary
    assert report.cra_events_submitted == 2, report.summary
    assert report.cra_month.status == "ok",  report.summary
    assert report.expenses_failed == 0
    assert report.cra_events_failed == 0


@pytest.mark.asyncio
async def test_mauvais_credentials():
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    s = ConfirmedSubmission(expenses=[
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05",
                    total_amount=10.0, description="Test")
    ])
    report = await run_submission(s, "mauvais@email.com", "wrongpass")

    assert report.expenses_submitted == 0
    assert report.expenses_failed == 1
    assert "authentification" in report.expenses[0].error.lower()


@pytest.mark.asyncio
async def test_echec_partiel_continue(monkeypatch):
    if not await _api_disponible():
        pytest.skip("Mock-API non accessible")

    import submit_expenses_core as core
    original = core._submit_one_expense
    appels = 0

    async def patched(client, token, index, expense):
        nonlocal appels
        appels += 1
        if appels == 2:
            from schemas import ExpenseResult
            return ExpenseResult(index=index, description=expense.description,
                                 total_amount=expense.total_amount,
                                 status="failed", error="Erreur simulee")
        return await original(client, token, index, expense)

    monkeypatch.setattr(core, "_submit_one_expense", patched)

    s = ConfirmedSubmission(expenses=[
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05",
                    total_amount=10, description="A"),
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05",
                    total_amount=20, description="B"),
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05",
                    total_amount=30, description="C"),
    ])
    report = await run_submission(s, EMAIL, PASSWORD)

    assert report.expenses_submitted == 2
    assert report.expenses_failed == 1
    assert any(r.error == "Erreur simulee" for r in report.expenses)