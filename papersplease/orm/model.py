import datetime
from typing import Optional

import pydantic.main
from sqlmodel import SQLModel, Field
from sqlalchemy import PrimaryKeyConstraint


class Account(SQLModel, table=True):
    email: str = Field(primary_key=True)
    password: str
    first_name: str
    last_name: str
    title: str
    affiliation: str


class Conference(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, default=None)
    name: str
    city: str
    state: str
    country: str
    start_date: datetime.date
    end_date: datetime.date
    paper_deadline: datetime.date
    chair: str = Field(foreign_key="account.email")


class Paper(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True, default=None)
    conference_id: int = Field(foreign_key="conference.id")
    title: str


class PaperAuthor(SQLModel, table=True):
    paper_id: int = Field(foreign_key="paper.id")
    author_email: str = Field(foreign_key="account.email")

    __table_args__ = (
        PrimaryKeyConstraint("paper_id", "author_email"),
    )


class Recommendation(pydantic.main.Enum):
    accept = "accept"
    neutral = "neutral"
    reject = "reject"
    pending = "pending"


class Assignment(SQLModel, table=True):
    reviewer_email: str = Field(foreign_key="account.email")
    paper_id: int = Field(foreign_key="paper.id")
    recommendation: Recommendation = Field(default=Recommendation.pending)

    __table_args__ = (
        PrimaryKeyConstraint("reviewer_email", "paper_id"),
    )


class DecisionStatus(pydantic.main.Enum):
    publish = "publish"
    do_not_publish = "do not publish"


class Decision(SQLModel, table=True):
    paper_id: int = Field(foreign_key="paper.id", primary_key=True)
    status: DecisionStatus
