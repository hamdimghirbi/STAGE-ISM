"""Unit tests for MCP schema validation and submission payloads.

These tests do not require a running API — they only test that Pydantic
validates inputs correctly and rejects invalid data with clear error messages.
"""

from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError
from schemas import (
    ConfirmedSubmission, CraActivity, CraCategory, CraEvent,
    CraMonthSubmit, ExpenseItem, ExpenseType,
)


# Mileage expenses (INDEMNITES_KM) do not require a receipt.
# This test verifies that no error is raised when receipt_path is None.
def test_km_sans_recu_valide():
    e = ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05", total_amount=45.0)
    assert e.receipt_path is None


# All non-KM expense types require a receipt.
# This test verifies that a ValidationError is raised when receipt_path is missing.
def test_restaurant_sans_recu_leve_erreur():
    with pytest.raises(ValidationError, match="receipt_path obligatoire"):
        ExpenseItem(type=ExpenseType.RESTAURANT, month="2026-05", total_amount=23.50)


# When a valid receipt path is provided, the expense should be accepted.
def test_restaurant_avec_recu_valide():
    e = ExpenseItem(type=ExpenseType.RESTAURANT, month="2026-05",
                    total_amount=23.50, receipt_path="/tmp/recu.pdf")
    assert e.receipt_path == "/tmp/recu.pdf"


# The month field must be in YYYY-MM format.
# "05-2026" is wrong — this test verifies it is rejected.
def test_mauvais_format_month():
    with pytest.raises(ValidationError):
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="05-2026", total_amount=10.0)


# The total_amount must be strictly positive.
# This test verifies that a negative amount is rejected.
def test_montant_negatif():
    with pytest.raises(ValidationError):
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05", total_amount=-5.0)


# A valid CRA event should default to nb=1.0 (a full working day).
def test_cra_event_valide():
    ev = CraEvent(categorie=CraCategory.TRAVAIL, activity=CraActivity.PRESTATION,
                  start_date="2026-05-05", end_date="2026-05-05")
    assert ev.nb == 1.0


# CRA event dates must be in YYYY-MM-DD format.
# "05/05/2026" is wrong — this test verifies it is rejected.
def test_cra_event_mauvais_format_date():
    with pytest.raises(ValidationError):
        CraEvent(categorie=CraCategory.TRAVAIL, activity=CraActivity.PRESTATION,
                 start_date="05/05/2026", end_date="05/05/2026")


# A ConfirmedSubmission with no expenses, no CRA events, and no cra_month is invalid.
# This prevents accidentally submitting an empty payload to Portalite.
def test_submission_vide_leve_erreur():
    with pytest.raises(ValidationError, match="Au moins une"):
        ConfirmedSubmission()


# A submission with only expenses (no CRA) should be accepted.
# cra_events and cra_month should default to empty/None.
def test_submission_expenses_seulement():
    s = ConfirmedSubmission(expenses=[
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05", total_amount=30.0)
    ])
    assert len(s.expenses) == 1
    assert s.cra_events == []
    assert s.cra_month is None


# A submission with only a CRA month declaration (no expenses) should be accepted.
def test_submission_cra_month_seulement():
    s = ConfirmedSubmission(cra_month=CraMonthSubmit(month="2026-05"))
    assert s.cra_month.month == "2026-05"
    assert s.expenses == []


# Month 13 does not exist — this test verifies it is rejected by the pattern validator.
def test_cra_month_mois_invalide():
    with pytest.raises(ValidationError):
        CraMonthSubmit(month="2026-13")