from sqlmodel import Field, SQLModel, create_engine
from .model import Account

sqlite_file_name = "db.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)
