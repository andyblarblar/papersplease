import datetime
import logging
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import Session, select
from starlette import status
from starlette.requests import Request

from .orm.connect import engine
from .orm.model import Account, AccountDTO, Paper, PaperAuthor, Conference
from .security.token import decode, OAuth2PasswordBearerWithCookie
from .orm import utils


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


async def get_user_roles(
    user: Annotated[AccountDTO, Depends(get_current_user)]
) -> utils.Roles:
    """Gets all roles the logged-in user participates in."""
    return utils.user_roles(user.email)


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


async def get_user_owned_paper(
    account: Annotated[AccountDTO, Depends(get_current_user)],
    sess: Annotated[Session, Depends(db_session)],
    paper_id: int,
) -> Paper:
    """Gets a paper owned by the user. 401s if user does not own, or it does not exist."""
    # Selects a paper with the selected author and paper ids
    res = sess.exec(
        select(Paper)
        .join(PaperAuthor, PaperAuthor.paper_id == Paper.id)
        .where(PaperAuthor.author_email == account.email and Paper.id == paper_id)
    ).first()

    if res:
        return res
    else:
        raise HTTPException(401, "This user does not have access to this paper")


async def get_avil_conferences(
    sess: Annotated[Session, Depends(db_session)],
) -> list[Conference]:
    """Returns all conferences that can be submitted too"""
    res = sess.exec(
        select(Conference).where(Conference.paper_deadline > datetime.datetime.utcnow())
    ).all()

    return res
