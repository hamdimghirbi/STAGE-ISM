from __future__ import annotations

"""Schema definitions for MCP submission payloads and results.

This file defines all Pydantic models used by the MCP tools.
Field names and enum values match the mock-api exactly so that
the payloads can be sent directly to Portalite without transformation.
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums — mirror app/enums.py in the mock-api exactly
# ---------------------------------------------------------------------------

# All expense types accepted by Portalite
class ExpenseType(str, Enum):
    INDEMNITES_KM   = "Indemnités kilométriques"
    AUTRE           = "Autre"
    RESTAURANT      = "Restaurant"
    MATERIEL        = "Materiel"
    TITRE_TRANSPORT = "Titre de transport"
    TELEPHONIE      = "Telephonie"
    TELETRAVAIL     = "Teletravail"


# Top-level CRA categories: either a work day or an absence
class CraCategory(str, Enum):
    ABSENCE = "Absence"
    TRAVAIL = "Travail"


# Specific activities within each category
# Travail: Prestation, HNO, Astreinte
# Absence: CP, RTT, Maladie, Sans solde, Autre
class CraActivity(str, Enum):
    PRESTATION = "Prestation"
    HNO        = "HNO"
    ASTREINTE  = "Astreinte"
    CP         = "CP"
    RTT        = "RTT"
    MALADIE    = "Maladie"
    SANS_SOLDE = "Sans solde"
    AUTRE      = "Autre"


# ---------------------------------------------------------------------------
# Input models — what Claude sends to the MCP tools
# ---------------------------------------------------------------------------

# Represents one expense to submit.
# Maps directly to the form fields of POST /api/expenses.
class ExpenseItem(BaseModel):
    type: ExpenseType
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")  # must be YYYY-MM
    total_amount: float = Field(..., gt=0)                         # must be positive
    description: str = Field(default="")
    billable_to_client: bool = Field(default=False)
    comment: str = Field(default="")
    receipt_path: Optional[str] = Field(None)                      # path to receipt file on disk

    @model_validator(mode="after")
    def receipt_obligatoire(self) -> "ExpenseItem":
        # All expense types require a receipt except mileage (INDEMNITES_KM).
        # This is validated before any API call so we fail fast with a clear message.
        if self.type != ExpenseType.INDEMNITES_KM and not self.receipt_path:
            raise ValueError(
                f"receipt_path obligatoire pour le type '{self.type.value}'."
            )
        return self


# Represents one CRA event (a day or range of days).
# Maps directly to the JSON body of POST /api/cra/events.
class CraEvent(BaseModel):
    categorie: CraCategory                                         # Travail or Absence
    activity: CraActivity                                          # Prestation, CP, RTT, etc.
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # must be YYYY-MM-DD
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    nb: float = Field(default=1.0, gt=0, le=1)                    # day fraction (0 to 1)
    all_day: bool = Field(default=True)
    description: str = Field(default="")


# Represents the monthly CRA declaration.
# Maps to the JSON body of POST /api/cra/month/{month}/submit.
# Also carries the worked-days breakdown for validation.
class CraMonthSubmit(BaseModel):
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    description_tasks: str = Field(default="")
    reserve_use_eur: float = Field(default=0.0, ge=0)
    reserve_use_days: float = Field(default=0.0, ge=0)
    reserve_save_eur: float = Field(default=0.0, ge=0)
    reserve_save_days: float = Field(default=0.0, ge=0)
    days_worked: float = Field(default=0.0, ge=0, le=23)          # working days
    leave_days: float = Field(default=0.0, ge=0)                  # CP, RTT, etc.
    public_holidays: float = Field(default=0.0, ge=0)             # jours fériés

    @model_validator(mode="after")
    def validate_days(self) -> "CraMonthSubmit":
        # The total of worked days + leave days + public holidays must not exceed 23.
        # 23 is the maximum number of working days in a month.
        # Validated at Pydantic level before any API call.
        total = self.days_worked + self.leave_days + self.public_holidays
        if total > 23:
            raise ValueError(
                f"Total days ({total}) exceeds maximum working days in a month (23)."
            )
        return self


# The full payload handed to submit_expenses after HITL validation.
# Groups expenses, CRA events, and the monthly declaration into one object.
class ConfirmedSubmission(BaseModel):
    expenses: list[ExpenseItem] = Field(default_factory=list)
    cra_events: list[CraEvent] = Field(default_factory=list)
    cra_month: Optional[CraMonthSubmit] = Field(None)

    @model_validator(mode="after")
    def au_moins_un_element(self) -> "ConfirmedSubmission":
        # Prevent submitting a completely empty payload.
        if not self.expenses and not self.cra_events and self.cra_month is None:
            raise ValueError("Au moins une note de frais ou une declaration CRA est requise.")
        return self


# ---------------------------------------------------------------------------
# Output models — what the MCP tools return to Claude
# ---------------------------------------------------------------------------

# Result for one expense submission attempt.
# expense_id is set if the API created the record successfully.
# receipt_uploaded tells Claude whether the file was attached.
class ExpenseResult(BaseModel):
    index: int
    description: str
    total_amount: float
    status: str                        # "ok" or "failed"
    expense_id: Optional[int] = None   # Portalite id if created
    error: Optional[str] = None        # error message if failed
    receipt_uploaded: Optional[bool] = None  # True if receipt was attached


# Result for one CRA event submission attempt.
class CraEventResult(BaseModel):
    index: int
    start_date: str
    end_date: str
    activity: str
    status: str                        # "ok" or "failed"
    event_id: Optional[int] = None
    error: Optional[str] = None


# Result for the monthly CRA declaration.
# status can be "ok", "failed", or "skipped" (if no cra_month was provided).
class CraMonthResult(BaseModel):
    status: str
    month: Optional[str] = None
    cra_month_id: Optional[int] = None
    error: Optional[str] = None


# The full report returned by submit_expenses to Claude.
# Claude shows the summary to the consultant and uses the detail lists
# to explain what succeeded and what failed.
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
    summary: str                       # human-readable one-liner for the consultant