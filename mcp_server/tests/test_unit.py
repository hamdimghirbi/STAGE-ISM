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


def test_km_sans_recu_valide():
    e = ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05", total_amount=45.0)
    assert e.receipt_path is None


def test_restaurant_sans_recu_leve_erreur():
    with pytest.raises(ValidationError, match="receipt_path obligatoire"):
        ExpenseItem(type=ExpenseType.RESTAURANT, month="2026-05", total_amount=23.50)


def test_restaurant_avec_recu_valide():
    e = ExpenseItem(type=ExpenseType.RESTAURANT, month="2026-05",
                    total_amount=23.50, receipt_path="/tmp/recu.pdf")
    assert e.receipt_path == "/tmp/recu.pdf"


def test_mauvais_format_month():
    with pytest.raises(ValidationError):
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="05-2026", total_amount=10.0)


def test_montant_negatif():
    with pytest.raises(ValidationError):
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05", total_amount=-5.0)


def test_cra_event_valide():
    ev = CraEvent(categorie=CraCategory.TRAVAIL, activity=CraActivity.PRESTATION,
                  start_date="2026-05-05", end_date="2026-05-05")
    assert ev.nb == 1.0


def test_cra_event_mauvais_format_date():
    with pytest.raises(ValidationError):
        CraEvent(categorie=CraCategory.TRAVAIL, activity=CraActivity.PRESTATION,
                 start_date="05/05/2026", end_date="05/05/2026")


def test_submission_vide_leve_erreur():
    with pytest.raises(ValidationError, match="Au moins une"):
        ConfirmedSubmission()


def test_submission_expenses_seulement():
    s = ConfirmedSubmission(expenses=[
        ExpenseItem(type=ExpenseType.INDEMNITES_KM, month="2026-05", total_amount=30.0)
    ])
    assert len(s.expenses) == 1
    assert s.cra_events == []
    assert s.cra_month is None


def test_submission_cra_month_seulement():
    s = ConfirmedSubmission(cra_month=CraMonthSubmit(month="2026-05"))
    assert s.cra_month.month == "2026-05"
    assert s.expenses == []


def test_cra_month_mois_invalide():
    with pytest.raises(ValidationError):
        CraMonthSubmit(month="2026-13")