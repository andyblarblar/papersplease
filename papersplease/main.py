import datetime
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, Response, Request, Query, Form
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import SQLModel, Session, select
from starlette import status
from starlette.responses import RedirectResponse

from .orm.connect import prepare_db
from .deps import (
    db_session,
    get_current_user,
    ensure_user_not_logged_in,
    get_user_roles,
    get_user_owned_paper,
    get_avil_conferences,
)
from .orm.model import (
    Account,
    AccountDTO,
    Paper,
    PaperAuthor,
    Assignment,
    Conference,
    Decision,
)
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
async def author_page(
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
async def author_paperview(
    request: Request,
    roles: Annotated[Roles, Depends(get_user_roles)],
    sess: Annotated[Session, Depends(db_session)],
    selected_paper: Annotated[Paper, Depends(get_user_owned_paper)],
):
    """Author paper view"""

    # Get metadata
    conf = sess.get(Conference, selected_paper.conference_id)
    dec = sess.get(Decision, selected_paper.id)
    authors = ",".join(
        sess.exec(
            select(PaperAuthor.author_email).where(
                PaperAuthor.paper_id == selected_paper.id
            )
        ).all()
    )

    decision_text = dec.status.value if dec else "Pending"

    return templates.TemplateResponse(
        "author_paperview.html.jinja",
        {
            "request": request,
            "roles": roles,
            "conference": conf,
            "decision": decision_text,
            "paper": selected_paper,
            "authors": authors,
        },
    )


@app.get("/author/papersub1")
async def author_sub_1(
    request: Request,
    roles: Annotated[Roles, Depends(get_user_roles)],
    conferences: Annotated[list[Conference], Depends(get_avil_conferences)],
):
    """Author paper submission first step"""

    return templates.TemplateResponse(
        "author_papersub1.html.jinja",
        {
            "request": request,
            "roles": roles,
            "conferences": conferences,
        },
    )


@app.get("/author/papersub2")
async def author_sub_2(
    request: Request,
    roles: Annotated[Roles, Depends(get_user_roles)],
    account: Annotated[AccountDTO, Depends(get_current_user)],
    conf_id: int,
):
    """Author paper submission second step"""

    return templates.TemplateResponse(
        "author_papersub2.html.jinja",
        {
            "request": request,
            "roles": roles,
            "conf_id": conf_id,
            "author": account.email,
        },
    )


@app.post("/author/paper", response_model=Paper, status_code=201)
async def paper_create(
    account: Annotated[AccountDTO, Depends(get_current_user)],
    sess: Annotated[Session, Depends(db_session)],
    paper_title: Annotated[str, Form()],
    authors: Annotated[str, Form()],
    conf_id: Annotated[int, Form()],
):
    """Creates a new paper"""

    authors = authors.split(",")
    conf_id = conf_id

    # Validate authors
    for author in authors:
        if not sess.get(Account, author):
            raise HTTPException(400, f"Email: {author} does not exist!")

    # Check deadline and ownership
    if sess.get(Conference, conf_id).paper_deadline < datetime.datetime.utcnow().date():
        raise HTTPException(400, "Conference submission deadline passed!")
    elif sess.exec(
        select(Account)
        .join(Conference, Conference == conf_id)
        .where(Account.email == Conference.chair)
    ).first():
        raise HTTPException(400, "Chairs cannot submit to their own conferences!")

    # Add paper
    paper_rec = Paper(conference_id=conf_id, title=paper_title)
    sess.add(paper_rec)
    sess.commit()

    # Then add authors
    author_recs = [
        PaperAuthor(author_email=email.strip(), paper_id=paper_rec.id)
        for email in authors
    ]
    sess.add_all(author_recs)
    sess.commit()

    return paper_rec


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
