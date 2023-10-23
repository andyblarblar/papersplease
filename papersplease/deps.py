import logging
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import Session
from starlette import status
from starlette.requests import Request

from .orm.connect import engine
from .orm.model import Account, AccountDTO
from .security.token import decode, OAuth2PasswordBearerWithCookie


def db_session() -> Session:
    """Creates a new db session"""
    sess = Session(engine)
    try:
        yield sess
    finally:
        sess.close()


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="token")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(db_session)],
) -> AccountDTO:
    """
    Authenticates the current user, and gets their account.
    If the user has no access token, they are sent to the logon page.
    If the user has an invalid token, they are logged out, then sent to the logon page.
    """
    data = decode(token)
    if not data:
        # If token bad, force user to destroy cookie to simplify
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer", "Location": "/logout"},
        )
    return AccountDTO.from_orm(db.get(Account, data.email))


async def ensure_user_not_logged_in(request: Request):
    """Ensures a logged in user does not see the login page."""
    # Redirect to home if logged in
    redirect = HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        detail="Already Authenticated",
        headers={"Location": "/"},
    )
    if token := request.cookies.get("access_token"):
        data = decode(token.removeprefix("bearer "))
        if data:
            raise redirect
