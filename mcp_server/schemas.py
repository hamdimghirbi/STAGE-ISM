from __future__ import annotations

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, model_validator


class ExpenseType(str, Enum):
    INDEMNITES_KM   = "Indemnités kilométriques"
    AUTRE           = "Autre"
    RESTAURANT      = "Restaurant"
    MATERIEL        = "Materiel"
    TITRE_TRANSPORT = "Titre de transport"
    TELEPHONIE      = "Telephonie"
    TELETRAVAIL     = "Teletravail"


class CraCategory(str, Enum):
    ABSENCE = "Absence"
    TRAVAIL = "Travail"


class CraActivity(str, Enum):
    PRESTATION = "Prestation"
    HNO        = "HNO"
    ASTREINTE  = "Astreinte"
    CP         = "CP"
    RTT        = "RTT"
    MALADIE    = "Maladie"
    SANS_SOLDE = "Sans solde"
    AUTRE      = "Autre"


class ExpenseItem(BaseModel):
    type: ExpenseType
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    total_amount: float = Field(..., gt=0)
    description: str = Field(default="")
    billable_to_client: bool = Field(default=False)
    comment: str = Field(default="")
    receipt_path: Optional[str] = Field(None)

    @model_validator(mode="after")
    def receipt_obligatoire(self) -> "ExpenseItem":
        if self.type != ExpenseType.INDEMNITES_KM and not self.receipt_path:
            raise ValueError(
                f"receipt_path obligatoire pour le type '{self.type.value}'."
            )
        return self


class CraEvent(BaseModel):
    categorie: CraCategory
    activity: CraActivity
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    nb: float = Field(default=1.0, gt=0, le=1)
    all_day: bool = Field(default=True)
    description: str = Field(default="")


class CraMonthSubmit(BaseModel):
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    description_tasks: str = Field(default="")
    reserve_use_eur: float = Field(default=0.0, ge=0)
    reserve_use_days: float = Field(default=0.0, ge=0)
    reserve_save_eur: float = Field(default=0.0, ge=0)
    reserve_save_days: float = Field(default=0.0, ge=0)
    days_worked: float = Field(default=0.0, ge=0, le=23)
    leave_days: float = Field(default=0.0, ge=0)
    public_holidays: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def validate_days(self) -> "CraMonthSubmit":
        total = self.days_worked + self.leave_days + self.public_holidays
        if total > 23:
            raise ValueError(
                f"Total days ({total}) exceeds maximum working days in a month (23)."
            )
        return self


class ConfirmedSubmission(BaseModel):
    expenses: list[ExpenseItem] = Field(default_factory=list)
    cra_events: list[CraEvent] = Field(default_factory=list)
    cra_month: Optional[CraMonthSubmit] = Field(None)

    @model_validator(mode="after")
    def au_moins_un_element(self) -> "ConfirmedSubmission":
        if not self.expenses and not self.cra_events and self.cra_month is None:
            raise ValueError("Au moins une note de frais ou une declaration CRA est requise.")
        return self


class ExpenseResult(BaseModel):
    index: int
    description: str
    total_amount: float
    status: str
    expense_id: Optional[int] = None
    error: Optional[str] = None
    receipt_uploaded: Optional[bool] = None


class CraEventResult(BaseModel):
    index: int
    start_date: str
    end_date: str
    activity: str
    status: str
    event_id: Optional[int] = None
    error: Optional[str] = None


class CraMonthResult(BaseModel):
    status: str
    month: Optional[str] = None
    cra_month_id: Optional[int] = None
    error: Optional[str] = None


class SubmissionReport(BaseModel):
    expenses_total: int
    expenses_submitted: int
    expenses_failed: int
    cra_events_total: int
    cra_events_submitted: int
    cra_events_failed: int
    expenses: list[ExpenseResult]
    cra_events: list[CraEventResult]
    cra_month: CraMonthResult
    summary: str