from datetime import date, datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, EmailStr, Field

from app.enums import CraActivity, CraCategory, ExpenseType, Status, UserRole

# ---------- Auth ----------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole

    class Config:
        from_attributes = True


# ---------- CRA events ----------


class CraEventBase(BaseModel):
    categorie: CraCategory
    activity: CraActivity
    start_date: date
    end_date: date
    all_day: bool = False
    nb: float = Field(default=1.0, gt=0, le=1)
    description: str = ''


class CraEventCreate(CraEventBase):
    pass


class CraEventUpdate(BaseModel):
    categorie: Optional[CraCategory] = None
    activity: Optional[CraActivity] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    all_day: Optional[bool] = None
    nb: Optional[float] = Field(default=None, gt=0, le=1)
    description: Optional[str] = None


class CraEventOut(CraEventBase):
    id: int
    user_id: int
    month: str

    class Config:
        from_attributes = True


# ---------- CRA month ----------


class CraMonthSubmit(BaseModel):
    description_tasks: str = ''
    reserve_use_eur: float = 0.0
    reserve_use_days: float = 0.0
    reserve_save_eur: float = 0.0
    reserve_save_days: float = 0.0


class CraMonthOut(BaseModel):
    id: int
    user_id: int
    month: str
    status: Status
    description_tasks: str
    reserve_use_eur: float
    reserve_use_days: float
    reserve_save_eur: float
    reserve_save_days: float
    signature_path: Optional[str]
    client_cra_path: Optional[str]
    submitted_at: Optional[datetime]
    validated_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------- Notes de frais ----------


class NoteFraisFilter(BaseModel):
    year: int
    month: Optional[int] = None  # 1..12
    status: Optional[Status] = None
    type: Optional[ExpenseType] = None
    billable: Optional[bool] = None
    page: int = 1
    limit: int = 10


class NoteFraisUpdate(BaseModel):
    type: Optional[ExpenseType] = None
    description: Optional[str] = None
    total_amount: Optional[float] = Field(default=None, gt=0)
    billable_to_client: Optional[bool] = None
    comment: Optional[str] = None


class NoteFraisOut(BaseModel):
    id: int
    user_id: int
    month: str
    type: ExpenseType
    description: str
    total_amount: float
    billable_to_client: bool
    comment: str
    receipt_path: Optional[str]
    status: Status
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Pagination ----------

T = TypeVar('T')


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    pages: int
    limit: int
