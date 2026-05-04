from datetime import datetime
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, func, select

from app.auth import get_current_user
from app.db import get_session
from app.enums import ExpenseType, Status
from app.files import save_upload
from app.models import NoteFrais, User
from app.schemas import NoteFraisFilter, NoteFraisOut, NoteFraisUpdate, Page

router = APIRouter()


@router.post('/filter', response_model=Page[NoteFraisOut])
def filter_expenses(
    payload: NoteFraisFilter,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> Page[NoteFraisOut]:
    stmt = select(NoteFrais).where(NoteFrais.user_id == current.id)
    count_stmt = select(func.count()).select_from(NoteFrais).where(NoteFrais.user_id == current.id)

    prefix = f'{payload.year:04d}-'
    stmt = stmt.where(NoteFrais.month.like(f'{prefix}%'))
    count_stmt = count_stmt.where(NoteFrais.month.like(f'{prefix}%'))

    if payload.month is not None:
        suffix = f'-{payload.month:02d}'
        stmt = stmt.where(NoteFrais.month.like(f'%{suffix}'))
        count_stmt = count_stmt.where(NoteFrais.month.like(f'%{suffix}'))
    if payload.status is not None:
        stmt = stmt.where(NoteFrais.status == payload.status)
        count_stmt = count_stmt.where(NoteFrais.status == payload.status)
    if payload.type is not None:
        stmt = stmt.where(NoteFrais.type == payload.type)
        count_stmt = count_stmt.where(NoteFrais.type == payload.type)
    if payload.billable is not None:
        stmt = stmt.where(NoteFrais.billable_to_client == payload.billable)
        count_stmt = count_stmt.where(NoteFrais.billable_to_client == payload.billable)

    total = session.exec(count_stmt).one()
    items = list(
        session.exec(
            stmt.order_by(NoteFrais.created_at.desc())
            .offset((payload.page - 1) * payload.limit)
            .limit(payload.limit)
        ).all()
    )
    pages = ceil(total / payload.limit) if total else 0
    return Page[NoteFraisOut](
        items=[NoteFraisOut.model_validate(i) for i in items],
        total=total,
        page=payload.page,
        pages=pages,
        limit=payload.limit,
    )


@router.post('', response_model=NoteFraisOut, status_code=201)
def create_expense(
    type: ExpenseType = Form(...),
    month: str = Form(...),  # 'YYYY-MM'
    description: str = Form(''),
    total_amount: float = Form(..., gt=0),
    billable_to_client: bool = Form(False),
    comment: str = Form(''),
    receipt: Optional[UploadFile] = File(default=None),
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> NoteFrais:
    if type != ExpenseType.INDEMNITES_KM and receipt is None:
        raise HTTPException(status_code=400, detail='Receipt required for this expense type')
    receipt_path = save_upload(receipt, current.id, 'receipts') if receipt else None
    nf = NoteFrais(
        user_id=current.id,
        month=month,
        type=type,
        description=description,
        total_amount=total_amount,
        billable_to_client=billable_to_client,
        comment=comment,
        receipt_path=receipt_path,
        status=Status.PENDING,
    )
    session.add(nf)
    session.commit()
    session.refresh(nf)
    return nf


@router.put('/{expense_id}', response_model=NoteFraisOut)
def update_expense(
    expense_id: int,
    payload: NoteFraisUpdate,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> NoteFrais:
    nf = session.get(NoteFrais, expense_id)
    if nf is None or nf.user_id != current.id:
        raise HTTPException(status_code=404, detail='Expense not found')
    if nf.status == Status.VALIDATED:
        raise HTTPException(status_code=409, detail='Expense already validated')
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(nf, k, v)
    nf.updated_at = datetime.utcnow()
    session.add(nf)
    session.commit()
    session.refresh(nf)
    return nf


@router.delete('/{expense_id}', status_code=204)
def delete_expense(
    expense_id: int,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> None:
    nf = session.get(NoteFrais, expense_id)
    if nf is None or nf.user_id != current.id:
        raise HTTPException(status_code=404, detail='Expense not found')
    if nf.status == Status.VALIDATED:
        raise HTTPException(status_code=409, detail='Cannot delete a validated expense')
    session.delete(nf)
    session.commit()
