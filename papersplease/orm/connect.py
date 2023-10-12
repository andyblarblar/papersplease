from sqlmodel import create_engine, SQLModel, Session, select
from ..security.password import password_context
from .model import Account

sqlite_file_name = "db.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)


def prepare_db():
    # Create tables if not exists
    SQLModel.metadata.create_all(engine)

    with Session(engine) as sess:
        # Add demo users if not exists
        if not sess.exec(select(Account).where(Account.email == "avealov@umich.edu")).first():
            a1 = Account(email="avealov@umich.edu", first_name="Andrew", last_name="Ealovega", title="Dr.",
                         affiliation="uofm dearborn", password=password_context.hash("123"))

            sess.add(a1)
            sess.commit()
