from fastapi import Depends
from sqlmodel import Session
from .orm.connect import engine


def db_session() -> Session:
    """Creates a new db session"""
    sess = Session(engine)
    try:
        yield sess
    finally:
        sess.close()
