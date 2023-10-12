from typing import Annotated

from fastapi import FastAPI, Depends
from sqlmodel import SQLModel, Session
from .orm.connect import prepare_db
from .deps import db_session
from .orm.model import Account, AccountDTO

app = FastAPI()


@app.on_event("startup")
def on_startup():
    prepare_db()


@app.get("/")
async def root(sess: Annotated[Session, Depends(db_session)]):
    return AccountDTO.from_orm(sess.get(Account, {'email': "avealov@umich.edu"}))
