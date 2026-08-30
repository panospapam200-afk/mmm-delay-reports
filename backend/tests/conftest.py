"""Κοινά fixtures για τα tests που χρειάζονται βάση δεδομένων.

Χρησιμοποιείται SQLite **στη μνήμη**: κάθε test ξεκινά με άδειο σχήμα και δεν
αφήνει τίποτα πίσω του. Έτσι το pipeline δεν χρειάζεται υπηρεσία PostgreSQL
για να τρέξει το στάδιο 2, και τα tests παραμένουν ανεξάρτητα μεταξύ τους.

Ο περιορισμός είναι γνωστός και δηλωμένος: το SQLite δεν είναι η PostgreSQL.
Γι' αυτό τα foreign keys ενεργοποιούνται ρητά (βλ. ``app/db.py``) — αλλιώς θα
δοκιμάζαμε ένα σύστημα με χαλαρότερους κανόνες από αυτό που παραδίδουμε.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  — καταχώριση των mappers πριν το create_all
from app.db import Base, get_session
from app.main import app
from app.models import Line, Report, ReportCategory, Stop, TransportMode, User, UserRole, utcnow
from app.security import create_access_token

# Σταθερή στιγμή αναφοράς: τα tests δεν εξαρτώνται ποτέ από το πραγματικό ρολόι.
NOW = datetime(2026, 9, 15, 8, 30, 0)


@pytest.fixture
def session() -> Iterator[Session]:
    # StaticPool: **μία** σύνδεση για όλα τα νήματα. Το FastAPI εκτελεί τα
    # σύγχρονα endpoints σε threadpool, και μια βάση SQLite στη μνήμη ζει μέσα
    # στη σύνδεση — με το προεπιλεγμένο pool κάθε νήμα θα έβλεπε δική του,
    # άδεια βάση («no such table: users»).
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session
    engine.dispose()


@pytest.fixture
def make_user(session: Session):
    counter = {"n": 0}

    def _make(
        *,
        role: UserRole = UserRole.PASSENGER,
        confirmations: int = 0,
        disputes: int = 0,
    ) -> User:
        counter["n"] += 1
        user = User(
            email=f"user{counter['n']}@example.com",
            password_hash="not-a-real-hash",
            role=role,
            confirmations_received=confirmations,
            disputes_received=disputes,
        )
        session.add(user)
        session.commit()
        return user

    return _make


@pytest.fixture
def make_line(session: Session):
    counter = {"n": 0}

    def _make(
        *,
        code: str | None = None,
        mode: TransportMode = TransportMode.BUS,
        stops: tuple[str, ...] = ("Αφετηρία", "Τέρμα"),
    ) -> Line:
        counter["n"] += 1
        line = Line(
            code=code or f"L{counter['n']}",
            name=f"Δοκιμαστική γραμμή {counter['n']}",
            mode=mode,
        )
        line.stops = [Stop(name=name, position=position) for position, name in enumerate(stops)]
        session.add(line)
        session.commit()
        return line

    return _make


def _report_factory(session: Session, reference: datetime):
    def _make(
        *,
        line: Line,
        author: User,
        delay: float,
        minutes_ago: float = 0,
        category: ReportCategory = ReportCategory.DELAY,
    ) -> Report:
        report = Report(
            line_id=line.id,
            author_id=author.id,
            delay_minutes=delay,
            category=category,
            created_at=reference - timedelta(minutes=minutes_ago),
        )
        session.add(report)
        session.commit()
        return report

    return _make


@pytest.fixture
def make_report(session: Session):
    """Αναφορά τοποθετημένη σε σχέση με τη σταθερή στιγμή ``NOW``.

    Για τα tests του πυρήνα και των υπηρεσιών, που περνούν το ίδιο ``NOW`` στη
    συνάρτηση συνάθροισης.
    """
    return _report_factory(session, NOW)


@pytest.fixture
def make_live_report(session: Session):
    """Αναφορά τοποθετημένη σε σχέση με το **πραγματικό** ρολόι.

    Απαραίτητη για τα tests του API: τα endpoints καλούν μόνα τους ``utcnow()``,
    οπότε αναφορές χτισμένες γύρω από το σταθερό ``NOW`` του 2026-09-15 θα
    φαίνονταν μελλοντικές και θα απορρίπτονταν ως αλλοιωμένες.
    """
    return _report_factory(session, utcnow())


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """TestClient που μοιράζεται τη συνεδρία των fixtures.

    Χωρίς την αντικατάσταση της εξάρτησης, το API θα μιλούσε στη βάση των
    ρυθμίσεων και τα tests θα έγραφαν σε πραγματικό αρχείο.
    """
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Κεφαλίδα Authorization για δεδομένο χρήστη.

    Παρακάμπτει σκόπιμα το endpoint σύνδεσης: τα tests των υπόλοιπων endpoints
    δεν πρέπει να αποτυγχάνουν επειδή χάλασε το login. Το login έχει τα δικά
    του tests.
    """

    def _make(user: User) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user.id, now=utcnow())}"}

    return _make
