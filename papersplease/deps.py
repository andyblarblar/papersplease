from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from starlette import status

from .orm.connect import engine
from .orm.model import Account, AccountDTO
from .security.token import decode


def db_session() -> Session:
    """Creates a new db session"""
    sess = Session(engine)
    try:
        yield sess
    finally:
        sess.close()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(db_session)],
) -> AccountDTO:
    """Authenticates the current user, and gets their account"""
    data = decode(token)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AccountDTO.from_orm(db.get(Account, data.email))
