import datetime

from sqlmodel import create_engine, SQLModel, Session, select
from ..security.password import password_context
from .model import Account, Conference, Assignment, Paper, PaperAuthor

sqlite_file_name = "db.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)


def prepare_db():
    # Create tables if not exists
    SQLModel.metadata.create_all(engine)

    with Session(engine) as sess:
        # Add demo users if not exists
        if not sess.exec(select(Account).where(Account.email == "avealov@umich.edu")).first():
            # A reviewer
            a1 = Account(email="avealov@umich.edu", first_name="Andrew", last_name="Ealovega", title="Dr.",
                         affiliation="uofm dearborn", password=password_context.hash("123"))
            # An author
            a3 = Account(email="laurasas@umich.edu", first_name="Laura", last_name="Sas",
                         title="Arts and Crafts Coordinator",
                         affiliation="uofm dearborn", password=password_context.hash("123"))
            # A chair
            a2 = Account(email="song@umich.edu", first_name="Zheng", last_name="Song", title="Dr.",
                         affiliation="uofm dearborn", password=password_context.hash("123"))

            c1 = Conference(name="VTC", city="Dearborn", state="MI", country="USA",
                            start_date=datetime.date(2024, 1, 1), end_date=datetime.date(2024, 1, 7),
                            paper_deadline=datetime.date(2023, 12, 15), chair="song@umich.edu")

            sess.add(a1)
            sess.add(a2)
            sess.add(a3)
            sess.add(c1)
            sess.commit()

            p1 = Paper(conference_id=c1.id, title="Sensingbay")

            sess.add(p1)
            sess.commit()

            pa1 = PaperAuthor(paper_id=p1.id, author_email="laurasas@umich.edu")

            r1 = Assignment(reviewer_email="avealov@umich.edu", paper_id=p1.id)

            sess.add(r1)
            sess.add(pa1)
            sess.commit()
