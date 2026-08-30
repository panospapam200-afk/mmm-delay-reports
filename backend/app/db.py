"""Σύνδεση με τη βάση δεδομένων και συνεδρίες SQLAlchemy.

Το ``app/core/`` δεν εισάγει ποτέ αυτό το module — η εξάρτηση πηγαίνει μόνο
προς μία κατεύθυνση: το HTTP layer και οι υπηρεσίες γνωρίζουν τη βάση, ο
πυρήνας της λογικής όχι.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Βάση για όλα τα μοντέλα ORM."""


def _engine_options(url: str) -> dict[str, object]:
    """Το SQLite χρειάζεται ρύθμιση που δεν ισχύει για PostgreSQL."""
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


settings = get_settings()
engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    **_engine_options(settings.database_url),  # type: ignore[arg-type]
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection: object, _record: object) -> None:
    """Το SQLite αγνοεί τα foreign keys εκτός αν ενεργοποιηθούν ρητά.

    Χωρίς αυτό, τα tests θα περνούσαν με δεδομένα που η PostgreSQL θα
    απέρριπτε — δηλαδή θα δοκιμάζαμε διαφορετικό σύστημα από αυτό που
    παραδίδουμε.
    """
    if type(dbapi_connection).__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_session() -> Iterator[Session]:
    """Εξάρτηση FastAPI: μία συνεδρία ανά αίτημα, με εγγυημένο κλείσιμο."""
    with SessionLocal() as session:
        yield session
