from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.enums import CraCategory, CraActivity, ExpenseType, Status, UserRole


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    full_name: str
    role: UserRole = Field(default=UserRole.MEMBER)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CraEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key='user.id', index=True)
    month: str = Field(index=True)  # 'YYYY-MM'
    categorie: CraCategory
    activity: CraActivity
    start_date: date
    end_date: date
    all_day: bool = Field(default=False)
    nb: float = Field(default=1.0)
    description: str = ''
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CraMonth(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key='user.id', index=True)
    month: str = Field(index=True)  # 'YYYY-MM'
    status: Status = Field(default=Status.DRAFT)
    description_tasks: str = ''
    reserve_use_eur: float = 0.0
    reserve_use_days: float = 0.0
    reserve_save_eur: float = 0.0
    reserve_save_days: float = 0.0
    signature_path: Optional[str] = None
    client_cra_path: Optional[str] = None
    submitted_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NoteFrais(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key='user.id', index=True)
    month: str = Field(index=True)  # 'YYYY-MM'
    type: ExpenseType
    description: str = ''
    total_amount: float = 0.0
    billable_to_client: bool = False
    comment: str = ''
    receipt_path: Optional[str] = None
    status: Status = Field(default=Status.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
