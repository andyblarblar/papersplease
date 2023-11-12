import datetime
from typing import Annotated

from fastapi import FastAPI, Depends, HTTPException, Response, Request, Query, Form
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlmodel import Session, select
from starlette import status
from starlette.responses import RedirectResponse

from papersplease.orm.connect import prepare_db
from papersplease.deps import (
    db_session,
    get_current_user,
    ensure_user_not_logged_in,
    get_user_roles,
    get_user_owned_paper,
    get_avil_conferences,
    get_owned_conferences,
)
from papersplease.orm.model import (
    Account,
    AccountDTO,
    Paper,
    PaperAuthor,
    Assignment,
    Conference,
    Decision,
    Recommendation,
    DecisionStatus,
)
from papersplease.orm.utils import Roles
from papersplease.security import password
from papersplease.security.token import Token, create_access_token

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

    authors = authors.split(",")[:-1]

    # Validate authors
    for author in authors:
        if not sess.get(Account, author):
            raise HTTPException(400, f"Email: {author} does not exist!")

    # Check deadline and ownership
    if sess.get(Conference, conf_id).paper_deadline < datetime.datetime.utcnow().date():
        raise HTTPException(400, "Conference submission deadline passed!")
    elif sess.exec(
        select(Account)
        .join(Conference, Conference.id == conf_id)
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


class ReccDTO(BaseModel):
    recommendation: str
    paper_id: int


@app.put("/assignments", response_model=Assignment)
async def recommendation_update(
    account: Annotated[AccountDTO, Depends(get_current_user)],
    sess: Annotated[Session, Depends(db_session)],
    dto: ReccDTO,
):
    """Updates a reviewers recommendation"""

    # Check if chair has already made decision
    if sess.exec(select(Decision).where(Decision.paper_id == dto.paper_id)).first():
        raise HTTPException(400, "Chair has already made decision!")

    # Check if user owns assignment
    if record := sess.exec(
        select(Assignment)
        .where(Assignment.paper_id == dto.paper_id)
        .where(Assignment.reviewer_email == account.email)
    ).first():
        # Update recommendation
        record.recommendation = dto.recommendation
        sess.add(record)
        sess.commit()
        sess.refresh(record)
    else:
        # Fail because assignment for this user does not exist
        raise HTTPException(403, "You do not own this assignment!")

    return record


@app.get("/assignments")
async def assignments_home(
    request: Request,
    sess: Annotated[Session, Depends(db_session)],
    roles: Annotated[Roles, Depends(get_user_roles)],
    account: Annotated[AccountDTO, Depends(get_current_user)],
):
    """Reviewer landing page"""

    assignments = sess.exec(
        select(Paper, Assignment)
        .where(Paper.id == Assignment.paper_id)
        .where(Assignment.reviewer_email == account.email)
    ).all()

    return templates.TemplateResponse(
        "reviewer.html.jinja",
        {"request": request, "roles": roles, "assignments": assignments},
    )


class AssignCreate(BaseModel):
    email: str
    paper_id: int


@app.post("/assignments", status_code=201, response_model=Assignment)
async def assignments_create(
    sess: Annotated[Session, Depends(db_session)],
    confs: Annotated[list[Conference], Depends(get_owned_conferences)],
    assign: AssignCreate,
):
    """Assigns a new author to a paper"""

    paper = sess.get(Paper, assign.paper_id)

    # Unsure reviewer does not own this paper
    if sess.exec(
        select(PaperAuthor)
        .where(PaperAuthor.paper_id == paper.id)
        .where(PaperAuthor.author_email == assign.email)
    ).first():
        raise HTTPException(400, "User cannot review own paper")

    # Ensure user owns conference
    if paper.conference_id not in (i.id for i in confs):
        raise HTTPException(403, "User does not own conference")

    # Ensure email exists
    if not sess.get(Account, assign.email):
        raise HTTPException(400, "Account does not exist")

    # Ensure only 3 can be assigned
    assignment_c = len(
        sess.exec(
            select(Assignment).where(assign.paper_id == Assignment.paper_id)
        ).all()
    )
    if assignment_c == 3:
        raise HTTPException(400, "All assignments are already assigned")

    # Ensure reviewer can only be assigned once
    if sess.exec(
        select(Assignment)
        .where(assign.paper_id == Assignment.paper_id)
        .where(Assignment.reviewer_email == assign.email)
    ).first():
        raise HTTPException(400, "Reviewer already assigned to paper")

    record = Assignment(reviewer_email=assign.email, paper_id=assign.paper_id)
    sess.add(record)
    sess.commit()

    return record


@app.get("/conferences")
async def chair_home(
    request: Request,
    roles: Annotated[Roles, Depends(get_user_roles)],
    confs: Annotated[list[Conference], Depends(get_owned_conferences)],
):
    """Chair landing page"""

    return templates.TemplateResponse(
        "chair.html.jinja",
        {"request": request, "roles": roles, "conferences": confs},
    )


@app.get("/conferences/papers")
async def chair_paperlist(
    request: Request,
    sess: Annotated[Session, Depends(db_session)],
    roles: Annotated[Roles, Depends(get_user_roles)],
    conf_id: int,
    confs: Annotated[list[Conference], Depends(get_owned_conferences)],
):
    """Chair conference level view"""

    # Ensure user owns conference
    if conf_id not in (i.id for i in confs):
        raise HTTPException(403, "User does not own conference")

    res = sess.exec(
        select(Paper, Decision)
        .where(Paper.conference_id == conf_id)
        .outerjoin(Decision, Decision.paper_id == Paper.id)
    ).all()

    return templates.TemplateResponse(
        "chair_paperlist.html.jinja",
        {"request": request, "roles": roles, "res": res},
    )


@app.get("/conferences/paper")
async def chair_paperview(
    request: Request,
    sess: Annotated[Session, Depends(db_session)],
    roles: Annotated[Roles, Depends(get_user_roles)],
    paper_id: int,
    confs: Annotated[list[Conference], Depends(get_owned_conferences)],
):
    """Chair paper level view"""

    (paper, decision) = sess.exec(
        select(Paper, Decision)
        .where(Paper.id == paper_id)
        .outerjoin(Decision, Decision.paper_id == Paper.id)
    ).first()

    # Ensure paper in owned conference
    if paper.conference_id not in (i.id for i in confs):
        raise HTTPException(403, "User does not own conference")

    assignments = sess.exec(
        select(Assignment).where(Assignment.paper_id == paper_id)
    ).all()

    conf = sess.get(Conference, paper.conference_id)

    authors = ",".join(
        sess.exec(
            select(PaperAuthor.author_email).where(PaperAuthor.paper_id == paper_id)
        ).all()
    )

    # Determining recommended decision
    decision_str = "so not publish"
    # If decision is made, then use it
    if decision:
        decision_str = decision.status.value
    else:
        # If not all reviews are in, it's pending
        if len(assignments) < 3 or Recommendation.pending in (
            dec.recommendation for dec in assignments
        ):
            decision_str = "pending"
        # If all reviews are accept, accept
        elif (
            assignments[0].recommendation == Recommendation.accept
            and assignments[1].recommendation == Recommendation.accept
            and assignments[2].recommendation == Recommendation.accept
        ):
            decision_str = "publish"
        else:
            decision_str = "do not publish"

    return templates.TemplateResponse(
        "chair_paperview.html.jinja",
        {
            "request": request,
            "roles": roles,
            "paper": paper,
            "decision": decision_str,
            "assignments": assignments,
            "assignment_count": len(assignments),
            "conference": conf,
            "authors": authors,
        },
    )


class DecisionDTO(BaseModel):
    decision: DecisionStatus
    paper_id: int


@app.post("/decision", response_model=Decision)
async def decision_update(
    sess: Annotated[Session, Depends(db_session)],
    decision: DecisionDTO,
    confs: Annotated[list[Conference], Depends(get_owned_conferences)],
):
    """Creates or updates a decision"""

    paper = sess.get(Paper, decision.paper_id)
    conf = sess.get(Conference, paper.conference_id)

    # Ensure paper in owned conference
    if paper.conference_id not in (i.id for i in confs):
        raise HTTPException(403, "User does not own conference")

    # Ensure conference has not started
    if datetime.datetime.utcnow().date() > conf.start_date:
        raise HTTPException(400, "Cannot change decision after conference has started")

    # Update or create record
    if record := sess.exec(
        select(Decision).where(Decision.paper_id == decision.paper_id)
    ).first():
        record.status = decision.decision
        sess.add(record)
        sess.commit()
    else:
        record = Decision(status=decision.decision, paper_id=decision.paper_id)
        sess.add(record)
        sess.commit()

    return record


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
