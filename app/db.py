"""Database engine, session factory and declarative base."""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.environ.get("TP_DATABASE_URL", "sqlite:///tp.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _enable_foreign_keys(connection, _record) -> None:
    """SQLite ignores foreign keys unless this pragma is on."""
    connection.execute("PRAGMA foreign_keys = ON")


SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all tables."""


def get_session() -> Iterator[Session]:
    """Yield a session per request."""
    with SessionLocal() as session:
        yield session
