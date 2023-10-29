from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, Response, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session, select
from starlette import status
from starlette.responses import RedirectResponse

from .orm.connect import prepare_db
from .deps import (
    db_session,
    get_current_user,
    ensure_user_not_logged_in,
    get_user_roles,
)
from .orm.model import Account, AccountDTO, Paper, PaperAuthor
from .orm.utils import Roles
from .security import password
from .security.token import Token, create_access_token

app = FastAPI()

templates = Jinja2Templates("papersplease/templates")
app.mount("/static", StaticFiles(directory="papersplease/static"), name="static")


@app.on_event("startup")
def on_startup():
    prepare_db()


@app.get("/")
async def root(request: Request, roles: Annotated[Roles, Depends(get_user_roles)]):
    """Home landing page for signed in users"""

    return templates.TemplateResponse(
        "home.html.jinja", {"request": request, "roles": roles}
    )


@app.get("/author")
async def root(
    request: Request,
    roles: Annotated[Roles, Depends(get_user_roles)],
    account: Annotated[AccountDTO, Depends(get_current_user)],
    sess: Annotated[Session, Depends(db_session)],
):
    """Main author page"""

    # Get users papers
    papers = sess.exec(
        select(Paper)
        .join(PaperAuthor, PaperAuthor.paper_id == Paper.id)
        .where(PaperAuthor.author_email == account.email)
    ).all()

    return templates.TemplateResponse(
        "author.html.jinja", {"request": request, "roles": roles, "papers": papers}
    )


@app.get("/author/paper")
async def root(
    request: Request,
    roles: Annotated[Roles, Depends(get_user_roles)],
    account: Annotated[AccountDTO, Depends(get_current_user)],
    sess: Annotated[Session, Depends(db_session)],
    paper_id: Annotated[int, Query()],
):
    """Author paper view"""
    # TODO
    pass


@app.get("/login")
async def login(request: Request, not_login=Depends(ensure_user_not_logged_in)):
    """Login page. Will redirect to home if already logged in."""
    return templates.TemplateResponse("login.html.jinja", {"request": request})


@app.post("/token", response_model=Token)
async def create_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], response: Response
):
    """Creates an OAuth2 token"""
    if password.verify_password(form.password, form.username):
        access_token = create_access_token(form.username)
        # Set token in cookie and respond as JSON
        response.set_cookie("access_token", f"bearer {access_token}", httponly=True)
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/logout")
async def logout():
    """Destroys the login token"""
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response
