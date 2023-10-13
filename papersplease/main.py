from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import SQLModel, Session
from starlette import status

from .orm.connect import prepare_db
from .deps import db_session, get_current_user
from .orm.model import Account, AccountDTO
from .security import password
from .security.token import Token, create_access_token

app = FastAPI()


@app.on_event("startup")
def on_startup():
    prepare_db()


@app.get("/", response_model=AccountDTO)
async def root(user: Annotated[AccountDTO, Depends(get_current_user)]):
    return user


@app.post("/token", response_model=Token)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """Creates an OAuth2 token"""
    if password.verify_password(form.password, form.username):
        access_token = create_access_token(form.username)
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
