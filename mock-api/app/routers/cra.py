from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile
from sqlmodel import Session, select

from app.auth import get_current_user
from app.db import get_session
from app.enums import ACTIVITY_BY_CATEGORY, Status
from app.files import save_upload
from app.models import CraEvent, CraMonth, User
from app.schemas import CraEventCreate, CraEventOut, CraEventUpdate, CraMonthOut, CraMonthSubmit

router = APIRouter()

MONTH_REGEX = r'^\\d{4}-(0[1-9]|1[0-2])$'


def _validate_event_payload(categorie, activity, start_date, end_date) -> None:
    allowed = ACTIVITY_BY_CATEGORY.get(categorie, [])
    if activity not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f'Activity {activity.value!r} not allowed for category {categorie.value!r}',
        )
    if end_date < start_date:
        raise HTTPException(status_code=400, detail='end_date must be >= start_date')


def _get_or_create_month(session: Session, user_id: int, month: str) -> CraMonth:
    cm = session.exec(
        select(CraMonth).where(CraMonth.user_id == user_id, CraMonth.month == month)
    ).first()
    if cm is None:
        cm = CraMonth(user_id=user_id, month=month, status=Status.DRAFT)
        session.add(cm)
        session.commit()
        session.refresh(cm)
    return cm


# ---------- Events ----------


@router.get('/events', response_model=list[CraEventOut])
def list_events(
    month: str = Query(..., pattern=MONTH_REGEX),
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> list[CraEvent]:
    return list(
        session.exec(
            select(CraEvent).where(
                CraEvent.user_id == current.id, CraEvent.month == month
            )
        ).all()
    )


@router.post('/events', response_model=CraEventOut, status_code=201)
def create_event(
    payload: CraEventCreate,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> CraEvent:
    _validate_event_payload(payload.categorie, payload.activity, payload.start_date, payload.end_date)
    month = payload.start_date.strftime('%Y-%m')
    cm = _get_or_create_month(session, current.id, month)
    if cm.status == Status.VALIDATED:
        raise HTTPException(status_code=409, detail='Month already validated')
    event = CraEvent(user_id=current.id, month=month, **payload.model_dump())
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.put('/events/{event_id}', response_model=CraEventOut)
def update_event(
    event_id: int,
    payload: CraEventUpdate,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> CraEvent:
    event = session.get(CraEvent, event_id)
    if event is None or event.user_id != current.id:
        raise HTTPException(status_code=404, detail='Event not found')
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(event, k, v)
    if event.end_date < event.start_date:
        raise HTTPException(status_code=400, detail='end_date must be >= start_date')
    allowed = ACTIVITY_BY_CATEGORY.get(event.categorie, [])
    if event.activity not in allowed:
        raise HTTPException(status_code=400, detail='Activity not allowed for category')
    event.month = event.start_date.strftime('%Y-%m')
    event.updated_at = datetime.utcnow()
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.delete('/events/{event_id}', status_code=204)
def delete_event(
    event_id: int,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> None:
    event = session.get(CraEvent, event_id)
    if event is None or event.user_id != current.id:
        raise HTTPException(status_code=404, detail='Event not found')
    session.delete(event)
    session.commit()


# ---------- Month submit / signature ----------


@router.post('/month/{month}/submit', response_model=CraMonthOut)
def submit_month(
    month: str = Path(..., pattern=MONTH_REGEX),
    payload: CraMonthSubmit = ...,
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> CraMonth:
    cm = _get_or_create_month(session, current.id, month)
    if cm.status == Status.VALIDATED:
        raise HTTPException(status_code=409, detail='Month already validated')
    cm.description_tasks = payload.description_tasks
    cm.reserve_use_eur = payload.reserve_use_eur
    cm.reserve_use_days = payload.reserve_use_days
    cm.reserve_save_eur = payload.reserve_save_eur
    cm.reserve_save_days = payload.reserve_save_days
    cm.status = Status.PENDING
    cm.submitted_at = datetime.utcnow()
    cm.updated_at = datetime.utcnow()
    session.add(cm)
    session.commit()
    session.refresh(cm)
    return cm


@router.post('/month/{month}/signature', response_model=CraMonthOut)
def upload_signature(
    month: str = Path(..., pattern=MONTH_REGEX),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current: User = Depends(get_current_user),
) -> CraMonth:
    cm = _get_or_create_month(session, current.id, month)
    cm.signature_path = save_upload(file, current.id, 'signatures')
    cm.updated_at = datetime.utcnow()
    session.add(cm)
    session.commit()
    session.refresh(cm)
    return cm
