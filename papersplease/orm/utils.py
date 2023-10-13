from enum import Flag, auto

from sqlmodel import Session, select

from .connect import engine
from .model import Account, Conference, PaperAuthor


def user_is_chair_of_any(email: str) -> bool:
    """Checks if user is a chair of any conference"""
    with Session(engine) as sess:
        res = sess.exec(select(Account).where(Account.email == email).join(Conference.chair == Account.email))

        return bool(res.first())


def user_is_author(email: str) -> bool:
    """Checks if user is an author"""
    with Session(engine) as sess:
        res = sess.exec(select(Account).where(Account.email == email).join(PaperAuthor.author_email == Account.email))

        return bool(res.first())


def user_is_reviewer(email: str) -> bool:
    """Checks if user is a reviewer"""
    with Session(engine) as sess:
        res = sess.exec(select(Account).where(Account.email == email).join(PaperAuthor.author_email == Account.email))

        return bool(res.first())


class Role(Flag):
    author = auto()
    reviewer = auto()
    chair = auto()


def user_roles(email: str) -> Role:
    """Gets all roles a user is a part of, globally. For use in UI, not per conference."""
    return (user_is_author(email) and Role.author) | (user_is_reviewer(email) and Role.reviewer) | (
                user_is_chair_of_any(email) and Role.chair)
