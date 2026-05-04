from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session

from app.auth import authenticate, create_access_token, get_current_user
from app.db import get_session
from app.models import User
from app.schemas import TokenResponse, UserOut

router = APIRouter()


@router.post('/login', response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session),
) -> TokenResponse:
    # OAuth2PasswordRequestForm exposes 'username' which we use as email
    user = authenticate(session, form.username, form.password)
    if user is None or user.id is None:
        raise HTTPException(status_code=401, detail='Invalid credentials')
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return TokenResponse(access_token=token)


@router.get('/me', response_model=UserOut)
def me(current: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current)
