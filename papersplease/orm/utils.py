from typing import NamedTuple

from sqlmodel import Session, select

from .connect import engine
from .model import Account, Conference, PaperAuthor, Assignment


def user_is_chair_of_any(email: str) -> bool:
    """Checks if user is a chair of any conference"""
    with Session(engine) as sess:
        res = sess.exec(
            select(Account)
            .where(Account.email == email)
            .join(Conference, Conference.chair == Account.email)
        )

        return bool(res.first())


def user_is_author(email: str) -> bool:
    """Checks if user is an author"""
    with Session(engine) as sess:
        res = sess.exec(
            select(Account)
            .where(Account.email == email)
            .join(PaperAuthor, PaperAuthor.author_email == Account.email)
        )

        return bool(res.first())


def user_is_reviewer(email: str) -> bool:
    """Checks if user is a reviewer"""
    with Session(engine) as sess:
        res = sess.exec(
            select(Account)
            .where(Account.email == email)
            .join(Assignment, Assignment.reviewer_email == Account.email)
        )

        return bool(res.first())


class Roles(NamedTuple):
    author: bool
    chair: bool
    reviewer: bool


def user_roles(email: str) -> Roles:
    """Gets all roles a user is a part of, globally. For use in UI, not per conference."""
    return Roles(
        author=user_is_author(email),
        chair=user_is_chair_of_any(email),
        reviewer=user_is_reviewer(email),
    )
