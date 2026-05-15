from datetime import datetime
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile
from sqlmodel import Session, func, select

from app.auth import get_current_user
from app.db import get_session
from app.files import save_upload
from app.models import CraMonth, User
from app.schemas import CraMonthOut, Page

router = APIRouter()

MONTH_REGEX = r'^\d{4}-(0[1-9]|1[0-2])$'


@router.get('/months', response_model=Page[CraMonthOut])
def list_months(
    year: Optional[int] = Query(default=None, ge=2000, le=2100),
    month: Optional[int] = Query(default=None, ge=1, le=12),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> Page[CraMonthOut]:
    stmt = select(CraMonth).where(CraMonth.user_id == current.id)
    count_stmt = select(func.count()).select_from(CraMonth).where(CraMonth.user_id == current.id)
    if year is not None:
        prefix = f'{year:04d}-'
        stmt = stmt.where(CraMonth.month.like(f'{prefix}%'))
        count_stmt = count_stmt.where(CraMonth.month.like(f'{prefix}%'))
    if month is not None:
        suffix = f'-{month:02d}'
        stmt = stmt.where(CraMonth.month.like(f'%{suffix}'))
        count_stmt = count_stmt.where(CraMonth.month.like(f'%{suffix}'))

    total = session.exec(count_stmt).one()
    items = list(
        session.exec(
            stmt.order_by(CraMonth.month.desc()).offset((page - 1) * limit).limit(limit)
        ).all()
    )
    pages = ceil(total / limit) if total else 0
    return Page[CraMonthOut](
        items=[CraMonthOut.model_validate(i) for i in items],
        total=total,
        page=page,
        pages=pages,
        limit=limit,
    )


@router.post('/months/{month}/import-client-cra', response_model=CraMonthOut)
def import_client_cra(
    month: str = Path(..., pattern=MONTH_REGEX),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> CraMonth:
    cm = session.exec(
        select(CraMonth).where(CraMonth.user_id == current.id, CraMonth.month == month)
    ).first()
    if cm is None:
        raise HTTPException(status_code=404, detail='CRA month not found')
    cm.client_cra_path = save_upload(file, current.id, 'client-cra')
    cm.updated_at = datetime.utcnow()
    session.add(cm)
    session.commit()
    session.refresh(cm)
    return cm
